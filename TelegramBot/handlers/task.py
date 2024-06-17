import re

from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as date_parser
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, CommandHandler, filters, \
    CallbackQueryHandler

from .basic_commands import cancel
from ..utils.api import get_user_tasks, update_task, create_task, get_user, delete_task, get_user_by_oid
from datetime import datetime, timezone, timedelta
from dateutil.parser import isoparse
from ..keyboards.reply_kb import active_tasks_keyboard, recurring_keyboard, member_list_keyboard
from ..keyboards.inline_kb import task_menu, task_action_buttons, confirmation_keyboard, edit_task_options_keyboard, \
    main_menu
from ..models import Task, GroupMember
from ..utils.states import reset_task_context, reset_all_context

db_to_user_recurring_map = {
    "daily": "Ежедневно",
    "weekly": "Еженедельно",
    "monthly": "Ежемесячно"
}

recurring_map = {
    "разовая": "False",
    "ежедневно": "daily",
    "еженедельно": "weekly",
    "ежемесячно": "monthly"
}


"""Viewing and completing tasks"""
(SELECT_TASK, CREATE_TASK_NAME, CREATE_TASK_DESCRIPTION, CREATE_TASK_DEADLINE, CREATE_TASK_RECURRING,
 CONFIRM_TASK_CREATION, SELECT_EDIT_OPTION,  HANDLE_TASK_ACTION, CONFIRM_TASK_EDIT, SELECT_TASK_ASSIGNEES) = range(10)


def generate_task_statistics(tasks: list[Task]):
    total_tasks = len(tasks)
    active_tasks = [task for task in tasks if task.status not in ['active', 'archive']]
    group_tasks = [task for task in active_tasks if task.group_oid]
    overdue_tasks = [task for task in active_tasks if isoparse(task.deadline) < datetime.now(timezone.utc)]
    nearest_deadline = min(active_tasks, key=lambda x: isoparse(x.deadline), default=None)

    nearest_deadline_str = nearest_deadline.deadline if nearest_deadline else "No active tasks"
    nearest_deadline_str = isoparse(nearest_deadline_str).strftime(
        "%d.%m %H:%M") if nearest_deadline else "No active tasks"

    stats = {
        'total_tasks': total_tasks,
        'active_tasks': len(active_tasks),
        'group_tasks': len(group_tasks),
        'overdue_tasks': len(overdue_tasks),
        'nearest_deadline': nearest_deadline_str
    }
    # active_tasks_sorted = sorted(active_tasks, key=lambda x: isoparse(x.deadline))
    return stats


def format_task_statistics_message(stats):
    return (
        f"ЗАДАЧИ\n\n"
        f"Всего задач: {stats['total_tasks']}\n"
        f"Активных: {stats['active_tasks']}\n"
        f"Из них групповых: {stats['group_tasks']}\n"
        f"Просрочено: {stats['overdue_tasks']}\n"
        f"Ближайший дедлайн: {stats['nearest_deadline']}"
    )


async def task_command(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_tid = user.id
    reset_all_context(context)
    tasks = await get_user_tasks(user_tid)
    stats = generate_task_statistics(tasks)
    context.user_data['tasks'] = tasks
    msg = await update.effective_user.send_message(format_task_statistics_message(stats), reply_markup=task_menu())
    return ConversationHandler.END


async def task_main_menu_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.from_user.delete_message(query.message.message_id)
    if query.data == 'active_tasks':
        user = query.from_user
        active_tasks = [task for task in context.user_data.get('tasks', []) if task.status not in ['archive', 'completed']]
        active_tasks_sorted = sorted(active_tasks, key=lambda x: isoparse(x.deadline))
        context.user_data['tasks_selected'] = active_tasks_sorted
        await update.effective_user.send_message("Выберите задачу: ",
                                                 reply_markup=active_tasks_keyboard(active_tasks_sorted))
        return SELECT_TASK
    elif query.data == 'new_task':
        await query.from_user.send_message("Введите название новой задачи:", reply_markup=ReplyKeyboardRemove())
        return CREATE_TASK_NAME
    elif query.data == 'personal_tasks':
        tasks = [task for task in context.user_data.get('tasks', []) if not task.group_oid]
        tasks_sorted = sorted(tasks, key=lambda x: isoparse(x.deadline))
        context.user_data['tasks_selected'] = tasks_sorted
        await update.effective_user.send_message("Выберите задачу: ",
                                                 reply_markup=active_tasks_keyboard(tasks_sorted))
    elif query.data == 'archive_tasks':
        active_tasks = [task for task in context.user_data.get('tasks', []) if task.status not in ['open', ]]
        active_tasks_sorted = sorted(active_tasks, key=lambda x: isoparse(x.deadline))
        context.user_data['tasks_selected'] = active_tasks_sorted
        await update.effective_user.send_message("Выберите задачу: ",
                                                 reply_markup=active_tasks_keyboard(active_tasks_sorted))


async def select_task(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    tasks_selected = context.user_data.get('tasks_selected', [])
    try:
        index = int(user_input.split(" - ")[0]) - 1
        selected_task = tasks_selected[index]
        context.user_data['current_task'] = selected_task
        recurrent = db_to_user_recurring_map.get(selected_task.recurring) if selected_task.recurring else "Нет"
        task_details = (
            f"\tЗадача {selected_task.title}\n"
            f"Описание: {selected_task.description}\n"
            f"Статус: {'Активна' if selected_task.status == 'open' else 'Закрыта'}\n"
            f"Дедлайн: {isoparse(selected_task.deadline).strftime('%d.%m.%y %H:%M')}\n"
            f"Цикличность: {recurrent}\n"
        )
        task_details += f"Завершена {selected_task.completion_date}" if selected_task.completion_date else ""
        msg = await update.message.reply_text(task_details,
                                              reply_markup=task_action_buttons(selected_task, update.effective_user.id))
        return HANDLE_TASK_ACTION
    except (IndexError, ValueError):
        await update.message.reply_text("Неправильный ввод. Попробуйте снова.")

        return SELECT_TASK


def calculate_next_occurrence(task: Task):
    current_deadline = isoparse(task.deadline)
    if task.recurring == "daily":
        next_occurrence = current_deadline + timedelta(days=1)
    elif task.recurring == "weekly":
        next_occurrence = current_deadline + timedelta(weeks=1)
    elif task.recurring == "monthly":
        next_occurrence = current_deadline + relativedelta(months=1)
    else:
        match = re.match(r'd(\d+)', task.recurring)
        if match:
            day_count = int(match.group(1))
            next_occurrence = current_deadline + timedelta(days=day_count)
        else:
            next_occurrence = None
    return next_occurrence.isoformat() if next_occurrence else None


async def complete_task_action(update, context) -> int:
    task = context.user_data.get("current_task")

    if not task:
        await update.effective_user.send_message("Ошибка! Задача не найдена.")
        await cancel(update, context)
        return ConversationHandler.END

    next_deadline_str = ""
    if task.recurring != "False":
        next_occurrence = calculate_next_occurrence(task)
        task.deadline = next_occurrence
        next_deadline_str = " Следующий дедлайн: " + isoparse(next_occurrence).strftime("%d.%m %H:%M")
    else:
        task.status = "completed"

    success = await update_task(task)
    if success:
        await update.effective_user.send_message("Задача отмечена как выполненная." + next_deadline_str)
    else:
        await update.effective_user.send_message("Не удалось отметить задачу как выполненную.")
    return ConversationHandler.END


async def delete_task_action(update: Update, context: CallbackContext) -> int:
    task = context.user_data.get('current_task')
    if not task:
        await update.effective_user.send_message("Ошибка! Задача не найдена.")
        return

    success = await delete_task(task.task_oid)
    if success:
        await update.effective_user.send_message("Задача успешно удалена.")
    else:
        await update.effective_user.send_message("Не удалось удалить задачу. Попробуйте снова.")
    context.user_data.pop('current_task', None)
    return ConversationHandler.END


async def edit_task_action(update: Update, context: CallbackContext) -> int:
    task = context.user_data.get('current_task')

    if not task:
        await update.effective_user.send_message("Ошибка! Задача не найдена.")
        await cancel(update, context)
        return ConversationHandler.END

    await update.effective_user.send_message("Что вы хотите изменить?", reply_markup=edit_task_options_keyboard())
    context.user_data['editing_task'] = True
    context.user_data['new_task'] = dict()
    return SELECT_EDIT_OPTION


async def handle_task_action(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    retval = -1
    await query.from_user.delete_message(query.message.message_id)
    if query.data == 'task_action_complete':
        retval = await complete_task_action(update, context)
    elif query.data == 'task_action_delete':
        retval = await delete_task_action(update, context)
    elif query.data == 'task_action_edit':
        retval = await edit_task_action(update, context)

    return retval


"""Creating tasks"""


async def confirm_task_creation(update: Update, context: CallbackContext) -> int:
    if context.user_data.get('editing_task'):
        await confirm_task_edit(update, context)
        return CONFIRM_TASK_EDIT
    task = context.user_data['new_task']
    assignee_names = context.user_data.get("task_assignee_names")
    recurrent = db_to_user_recurring_map.get(task['recurring']) if task['recurring'] else "Нет"
    confirmation_message = (
        f"Подтвердите создание задачи:\n"
        f"Название: {task['title']}\n"
        f"Описание: {task['description']}\n"
        f"Дедлайн: {isoparse(task['deadline']).strftime('%d.%m.%y %H:%M')}\n"
        f"Периодичность: {recurrent}"
    )
    confirmation_message += f"\nНазначена: {', '.join(assignee_names)}" if assignee_names else ""
    confirmation_message += "\n\nОтменить - /cancel"
    await update.message.reply_text(confirmation_message, reply_markup=confirmation_keyboard())
    return CONFIRM_TASK_CREATION


async def input_task_name(update: Update, context: CallbackContext) -> int:
    task_name = update.message.text
    if context.user_data.get('editing_new_task'):
        context.user_data['new_task']['title'] = task_name
        context.user_data['editing_new_task'] = False
        retval = await confirm_task_creation(update, context)
        return retval

    context.user_data['new_task'] = {'title': task_name}
    await update.message.reply_text("Введите описание задачи:")
    return CREATE_TASK_DESCRIPTION


async def input_task_description(update: Update, context: CallbackContext) -> int:
    task_description = update.message.text
    context.user_data['new_task']['description'] = task_description
    if context.user_data.get('editing_new_task'):
        context.user_data['editing_new_task'] = False
        retval = await confirm_task_creation(update, context)
        return retval
    await update.message.reply_text("Введите дедлайн задачи (дд.мм.*гггг чч:мм)\n"
                                    "*Текущий год можно не вводить, будет подставлен автоматически")
    return CREATE_TASK_DEADLINE


async def input_task_deadline(update: Update, context: CallbackContext) -> int:
    deadline_input = update.message.text
    current_year = datetime.now().year
    try:
        if len(deadline_input.split()) == 2:
            deadline = date_parser(deadline_input, dayfirst=True)
            if deadline.year == 1900:
                deadline = deadline.replace(year=current_year)
            deadline = deadline.replace(tzinfo=update.message.date.tzinfo)
        else:
            raise ValueError("Invalid format")

        context.user_data['new_task']['deadline'] = deadline.isoformat()
        if context.user_data.get('editing_new_task'):
            context.user_data['editing_new_task'] = False
            retval = await confirm_task_creation(update, context)
            return retval
        await update.message.reply_text("Укажите периодичность задачи (выберите из предложенных"
                                        " или укажите своё <число> дней):", reply_markup=recurring_keyboard())
        return CREATE_TASK_RECURRING
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Пожалуйста, введите дедлайн задачи (дд.мм.*гггг чч:мм):\n"
                                        "*Текущий год можно не вводить, будет подставлен автоматически")
        return CREATE_TASK_DEADLINE


async def input_task_recurring(update: Update, context: CallbackContext) -> int:
    recurring = update.message.text.lower()
    if recurring in recurring_map:
        context.user_data['new_task']['recurring'] = recurring_map[recurring]
        retval = await confirm_task_creation(update, context)
        return retval
    else:
        await update.message.reply_text("Неверный выбор. Пожалуйста, выберите периодичность из предложенных "
                                        "вариантов или введите своё <число> дней:", reply_markup=recurring_keyboard())
        return CREATE_TASK_RECURRING


async def handle_confirmation(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'task_confirm_yes':
        await query.message.delete()
        user_id = update.effective_user.id
        user_data = await get_user(user_id)
        assignees = context.user_data.get('task_assignees', None)
        new_task_data = {
            'title': context.user_data['new_task']['title'],
            'description': context.user_data['new_task']['description'],
            'status': 'open',
            'group_oid': context.user_data.get('current_group', ""),
            'deadline': context.user_data['new_task']['deadline'],
            'recurring': context.user_data['new_task']['recurring'],
            'assigned_to': [a.member_oid for a in assignees] if assignees else [user_data.user_oid],
            'creator_oid': user_data.user_oid,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'notified': {"day_before": False, "week_before": False}}
        task = Task(task_oid='-', **new_task_data)
        response = await create_task(task)
        if response.status == 201:
            await query.message.reply_text("Задача создана.", reply_markup=main_menu())
        else:
            await query.message.reply_text("Не удалось создать задачу. Попробуйте снова.", reply_markup=main_menu())
        reset_task_context(context)
        return ConversationHandler.END
    elif query.data == 'task_confirm_edit':
        await query.message.delete()
        group_task = len(context.user_data.get('task_assignees', [])) > 0
        edit_message = await query.message.reply_text("Что вы хотите изменить?",
                                                      reply_markup=edit_task_options_keyboard(group_task))
        context.user_data['edit_message_id'] = edit_message.message_id
        return SELECT_EDIT_OPTION


async def handle_edit_option(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.from_user.delete_message(query.message.message_id)
    await query.answer()
    if query.data == 'task_edit_title':
        await query.message.reply_text("Введите новое название задачи:")
        context.user_data['editing_new_task'] = True
        return CREATE_TASK_NAME
    elif query.data == 'task_edit_description':
        await query.message.reply_text("Введите новое описание задачи:")
        context.user_data['editing_new_task'] = True
        return CREATE_TASK_DESCRIPTION
    elif query.data == 'task_edit_deadline':
        await query.message.reply_text("Введите новый дедлайн задачи (дд.мм.*гггг чч:мм)\n*Текущий год можно не вводить, будет подставлен автоматически")
        context.user_data['editing_new_task'] = True
        return CREATE_TASK_DEADLINE
    elif query.data == 'task_edit_recurring':
        await query.message.reply_text("Укажите новую периодичность задачи (выберите из предложенных или укажите своё <число> дней):", reply_markup=recurring_keyboard())
        context.user_data['editing_new_task'] = True
        return CREATE_TASK_RECURRING
    elif query.data == 'task_edit_assignees':
        group = context.user_data['current_group']
        await query.message.reply_text("Выберите новых пользователей:",
                                       reply_markup=member_list_keyboard(group.members))
        context.user_data['editing_new_task'] = True
        return SELECT_TASK_ASSIGNEES


"""Editing tasks"""


async def get_assignee_names(assignee_list: list):
    names = list()
    for member in assignee_list:
        oid = member.member_oid if isinstance(member, GroupMember) else member
        user = await get_user_by_oid(oid)
        names.append(user.name)
    return names


async def confirm_task_edit(update: Update, context: CallbackContext):
    current_task = context.user_data.get('current_task')
    new_data = context.user_data.get('new_task')
    assignee_names = await get_assignee_names(context.user_data.get("task_assignees", current_task.assigned_to))
    current_task.title = new_data.get('title', current_task.title)
    current_task.description = new_data.get('description', current_task.description)
    current_task.deadline = new_data.get('deadline', current_task.deadline)
    current_task.recurring = new_data.get('recurring', current_task.recurring)
    current_task.assigned_to = context.user_data.get("task_assignees", current_task.assigned_to)
    recurrent = db_to_user_recurring_map.get(current_task.recurring) if current_task.recurring else "Нет"
    confirmation_message = (
        f"Подтвердите новые значения для задачи:\n"
        f"Название: {current_task.title}\n"
        f"Описание: {current_task.description}\n"
        f"Дедлайн: {isoparse(current_task.deadline).strftime('%d.%m.%y %H:%M')}\n"
        f"Периодичность: {recurrent}"
    )
    confirmation_message += f"\nНазначена: {', '.join(assignee_names)}" if assignee_names else ""
    confirmation_message += "\n\nОтменить - /cancel"
    await update.message.reply_text(confirmation_message, reply_markup=confirmation_keyboard())


async def handle_edit_confirmation(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'task_confirm_yes':
        await query.message.delete()
        task = context.user_data.get('current_task')
        task.last_updated = datetime.now(timezone.utc).isoformat()
        success = await update_task(task)
        if success:
            await query.message.reply_text("Задача обновлена", reply_markup=main_menu())
        else:
            await query.message.reply_text("Не удалось обновить задачу. Попробуйте снова.",
                                           reply_markup=main_menu())
        reset_task_context(context)
        return ConversationHandler.END
    elif query.data == 'task_confirm_edit':
        await query.message.delete()
        edit_message = await query.message.reply_text("Что вы хотите изменить?", reply_markup=edit_task_options_keyboard())
        return SELECT_EDIT_OPTION


task_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(task_main_menu_callback,
                                       pattern=r'^(active_tasks|new_task|personal_tasks|archive_tasks)$')],
    states={
        SELECT_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_task)],
        CREATE_TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_name)],
        CREATE_TASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_description)],
        CREATE_TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_deadline)],
        CREATE_TASK_RECURRING: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_recurring)],
        CONFIRM_TASK_CREATION: [CallbackQueryHandler(handle_confirmation, pattern=r'^task_confirm')],
        SELECT_EDIT_OPTION: [CallbackQueryHandler(handle_edit_option, pattern=r'^task_edit')],
        HANDLE_TASK_ACTION: [CallbackQueryHandler(handle_task_action, pattern=r'^task_action_')],
        CONFIRM_TASK_EDIT: [CallbackQueryHandler(handle_edit_confirmation, pattern=r'^task_confirm')]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)


