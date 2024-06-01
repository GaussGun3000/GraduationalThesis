import re

from dateutil.relativedelta import relativedelta
from dateutil.parser import parser as date_parser
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, CommandHandler, filters, \
    CallbackQueryHandler

from .basic_commands import cancel
from ..utils.api import get_user_tasks, update_task, create_task, get_user
from datetime import datetime, timezone, timedelta
from dateutil.parser import isoparse
from ..keyboards.reply_kb import active_tasks_keyboard, recurring_keyboard
from ..keyboards.inline_kb import task_menu, task_action_buttons
from ..models import Task


"""Viewing and completing tasks"""
SELECT_TASK, CREATE_TASK_NAME, CREATE_TASK_DESCRIPTION, CREATE_TASK_DEADLINE, CREATE_TASK_RECURRING = range(5)


def generate_task_statistics(tasks: list[Task]):
    total_tasks = len(tasks)
    active_tasks = [task for task in tasks if task.status not in ['active', 'archive']]
    group_tasks = [task for task in active_tasks if task.group_oid]
    overdue_tasks = [task for task in active_tasks if isoparse(task.deadline) < datetime.now(timezone.utc)]
    nearest_deadline = min(active_tasks, key=lambda x: isoparse(x.deadline), default=None)

    nearest_deadline_str = nearest_deadline.deadline if nearest_deadline else "No active tasks"
    nearest_deadline_str = isoparse(nearest_deadline_str).strftime(
        "%d:%m %H:%M") if nearest_deadline else "No active tasks"

    stats = {
        'total_tasks': total_tasks,
        'active_tasks': len(active_tasks),
        'group_tasks': len(group_tasks),
        'overdue_tasks': len(overdue_tasks),
        'nearest_deadline': nearest_deadline_str
    }

    active_tasks_sorted = sorted(active_tasks, key=lambda x: isoparse(x.deadline))

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


async def task_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_tid = user.id

    tasks = await get_user_tasks(user_tid)
    stats = generate_task_statistics(tasks)
    context.user_data['tasks'] = tasks
    msg = await update.message.reply_text(format_task_statistics_message(stats), reply_markup=task_menu())
    context.user_data['last_message'] = msg


async def task_main_menu_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'active_tasks':
        user = query.from_user
        await query.from_user.delete_message(query.message.message_id)
        active_tasks = [task for task in context.user_data.get('tasks', []) if task.status not in ['active', 'archive']]
        active_tasks_sorted = sorted(active_tasks, key=lambda x: isoparse(x.deadline))
        context.user_data['tasks_selected'] = active_tasks_sorted
        await update.effective_user.send_message("Выберите задачу: ",
                                                 reply_markup=active_tasks_keyboard(active_tasks_sorted))
        return SELECT_TASK
    elif query.data == 'new_task':
        await query.from_user.delete_message(query.message.message_id)
        await query.from_user.send_message("Введите название новой задачи:")
        return CREATE_TASK_NAME


async def select_task(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    tasks_selected = context.user_data.get('tasks_selected', [])

    try:
        index = int(user_input.split(" - ")[0]) - 1
        selected_task = tasks_selected[index]
        context.user_data['current_task'] = selected_task
        task_details = (
            f"\tЗадача {selected_task.title}\n"
            f"Описание: {selected_task.description}\n"
            f"Статус: {selected_task.status}\n"
            f"Дедлайн: {isoparse(selected_task.deadline).strftime('%d:%m:%y %H:%M')}\n"
            f"Цикличность: {selected_task.recurring}\n"
        )
        task_details += f"Завершена {selected_task.completion_date}" if selected_task.completion_date else ""
        msg = await update.message.reply_text(task_details,
                                              reply_markup=task_action_buttons(selected_task, update.effective_user.id))
        context.user_data['last_message'] = msg
        return ConversationHandler.END
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


async def complete_task_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    task = context.user_data.get("current_task")
    await query.from_user.delete_message(query.message.message_id)
    if not task:
        await query.from_user.send_message("Ошибка! Задача не найдена.")
        return

    if task.recurring != "False":
        next_occurrence = calculate_next_occurrence(task)
        task.deadline = next_occurrence
    else:
        task.status = "completed"

    success = await update_task(task.task_oid, task)
    if success:
        await query.from_user.send_message("Задача отмечена как выполненная.")
    else:
        await query.from_user.send_message("Не удалось отметить задачу как выполненную.")


"""Creating tasks"""


async def input_task_name(update: Update, context: CallbackContext) -> int:
    task_name = update.message.text
    context.user_data['new_task'] = {'title': task_name}
    await update.message.reply_text("Введите описание задачи:")
    return CREATE_TASK_DESCRIPTION


async def input_task_description(update: Update, context: CallbackContext) -> int:
    task_description = update.message.text
    context.user_data['new_task']['description'] = task_description
    await update.message.reply_text("Введите дедлайн задачи (дд.мм.*гггг чч:мм)\n"
                                    "*Текущий год можно не вводить, будет подставлен автоматически")
    return CREATE_TASK_DEADLINE


async def input_task_deadline(update: Update, context: CallbackContext) -> int:
    from dateutil.parser import parse

    deadline_input = update.message.text
    current_year = datetime.now().year
    try:
        if len(deadline_input.split()) == 2:
            deadline = parse(deadline_input, dayfirst=True)
            if deadline.year == 1900:
                deadline = deadline.replace(year=current_year)
            deadline.replace(tzinfo=update.message.date.tzinfo)
        else:
            raise ValueError("Invalid format")

        context.user_data['new_task']['deadline'] = deadline.isoformat()
        await update.message.reply_text("Укажите периодичность задачи (выберите из предложенных"
                                        " или укажите своё <число> дней):", reply_markup=recurring_keyboard())
        return CREATE_TASK_RECURRING
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Пожалуйста, введите дедлайн задачи (дд.мм.*гггг чч:мм):\n"
                                        "*Текущий год можно не вводить, будет подставлен автоматически")
        return CREATE_TASK_DEADLINE


async def input_task_recurring(update: Update, context: CallbackContext) -> int:
    recurring_map = {}
    recurring = update.message.text
    user_id = update.effective_user.id
    context.user_data['new_task']['recurring'] = recurring
    user_data = await get_user(user_id)
    new_task_data = {
        'title': context.user_data['new_task']['title'],
        'description': context.user_data['new_task']['description'],
        'status': 'active',
        'deadline': context.user_data['new_task']['deadline'],
        'recurring': context.user_data['new_task']['recurring'],
        'assigned_to': [user_id],
        'creator_oid': user_data.user_oid,
        'last_updated': datetime.now(timezone.utc).isoformat()
    }
    task = Task(task_oid='-', **new_task_data)
    response = await create_task(task)
    if response.status == 201:
        await update.message.reply_text("Задача создана.")
    else:
        await update.message.reply_text("Не удалось создать задачу. Попробуйте снова.")
    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    await update.message.reply_text(f"Отмена операции, {user.full_name}.")
    return ConversationHandler.END


task_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(task_main_menu_callback,
                                       pattern=r'^(active_tasks|new_task|personal_tasks|archive_tasks)$')],
    states={
        SELECT_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_task)],
        CREATE_TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_name)],
        CREATE_TASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_description)],
        CREATE_TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_deadline)],
        CREATE_TASK_RECURRING: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_recurring)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)


