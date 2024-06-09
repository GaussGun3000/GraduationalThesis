from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, Message
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, CommandHandler, filters, \
    CallbackQueryHandler

from .basic_commands import cancel
from .financial import get_finance_statistics, set_reset_day, category_menu_callback, create_category_name, \
    create_category_description, handle_edit_fin_option, handle_category_edit_confirm, handle_category_confirm, \
    create_category_budget_limit, select_category, input_expense_description, input_expense_amount, \
    handle_expense_confirm, get_statistics_by_categories
from .task import select_task, input_task_name, input_task_description, input_task_deadline, input_task_recurring, \
    handle_confirmation, handle_edit_option, handle_task_action, handle_edit_confirmation, confirm_task_creation
from ..utils.api import (get_user, get_financial_info, create_financial, get_group, create_group, get_user_groups,
                         get_created_group, add_group_member, update_group, set_member_role, update_group_members,
                         get_group_tasks)
from datetime import datetime, timezone, timedelta
from dateutil.parser import isoparse
from ..keyboards.reply_kb import active_tasks_keyboard, recurring_keyboard, generate_category_keyboard, \
    admin_list_keyboard, member_list_keyboard, go_back_kb
from ..keyboards.inline_kb import financial_menu, category_menu, select_group_keyboard, confirm_or_edit_keyboard, edit_group_options_keyboard, \
    group_actions, menu_or_exit, admin_action_keyboard, member_action_keyboard, task_management_keyboard, \
    group_financial_menu, back_or_exit
from ..models import Group, GroupMember, User, Financial
from ..utils.states import reset_group_context, reset_all_context
from ..config import BOT_URL

(CREATE_GROUP_NAME, CREATE_GROUP_DESCRIPTION, ADD_GROUP_MEMBERS, CONFIRM_GROUP_CREATION, EDIT_GROUP,
 EDIT_EXISTING_GROUP, SELECT_GROUP_OPTION, GROUP_MENU_OR_EXIT, MANAGE_ADMINS, ADMIN_ACTION, SELECT_NEW_ADMIN,
 MANAGE_MEMBERS, MEMBER_ACTION, INPUT_NEW_MEMBER, MANAGE_TASKS,) = range(15)


async def group_command(update: Update, context: CallbackContext) -> int:
    reset_all_context(context)
    user_tid = update.effective_user.id
    created_group = await get_created_group(user_tid)
    user_groups = await get_user_groups(user_tid)
    user_data = await get_user(user_tid)
    context.user_data['user_data-db'] = user_data
    if created_group:
        context.user_data['my_group'] = created_group
    if not created_group and not user_groups and not user_data.is_premium():
        await update.message.reply_text("Вы не состоите в группах и у вас нет премиума для создания группы.")
        return ConversationHandler.END

    await update.message.reply_text("Выберите группу для управления:",
                                    reply_markup=select_group_keyboard(user_data, created_group, user_groups))
    return ConversationHandler.END


async def display_group_info(update: Update, context: CallbackContext) -> None:
    group = context.user_data.get('current_group')
    if not group:
        await update.message.reply_text("Ошибка: Группа не найдена.")
        return
    member_info = next((member for member in group.members if member.member_tid == update.effective_user.id), None)
    context.user_data['member_info'] = member_info
    member_count = len(group.members)
    group_info = (
        f"Группа {group.name}\n"
        f"Описание: {group.description}\n"
        f"Число участников: {member_count}\n"
    )
    if member_info.role == "creator":
        admin_count = sum(1 for member in group.members if member.role == 'admin')
        group_info += f"\nЧисло администраторов: {admin_count}"

    await update.effective_user.send_message(group_info, reply_markup=group_actions(member_info.role))


async def group_selection_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    user_tid = update.effective_user.id
    user_data = context.user_data['user_data-db']
    await query.message.delete()
    if query.data == 'group_my':
        created_group = context.user_data.get('my_group')
        if not created_group:
            await query.message.reply_text("У вас ещё не создана группа. Введите название для своей группы:",
                                           reply_markup=ReplyKeyboardRemove())
            return CREATE_GROUP_NAME
        else:
            created_group = await get_group(created_group)
            context.user_data['current_group'] = created_group
            await display_group_info(update, context)
            return SELECT_GROUP_OPTION

    if query.data.startswith('group_'):
        group_id = query.data.split('_')[1]
        await query.message.reply_text(f"Вы выбрали группу с ID: {group_id}")
        return ConversationHandler.END


async def manage_group_admins(update: Update, context: CallbackContext):
    group = context.user_data['current_group']
    admin_list = [member for member in group.members if member.role == 'admin']
    context.user_data['admins'] = admin_list
    msg = await update.effective_user.send_message('Выберите администратора для изменений, или "Новый админ", чтобы '
                                                   'выбрать нового, или "Назад", чтобы вернутся в предыдущее меню',
                                                   reply_markup=await admin_list_keyboard(admin_list))
    context.user_data['prev_message'] = msg


async def manage_group_members(update: Update, context: CallbackContext):
    group = context.user_data['current_group']
    member_list = [member for member in group.members if member.role != 'creator']
    context.user_data['member_list'] = member_list
    reply_markup = await member_list_keyboard(member_list)
    msg = await update.effective_user.send_message("Для приглашения пользователей в группу можно использовать "
                                                   f"ссылку: `{generate_invite_link(group.group_oid)}`\n\n"
                                                   f"Выберите участника для управления:",
                                                   reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['prev_message'] = msg


async def manage_group_tasks(update: Update, context: CallbackContext):
    member_info = context.user_data.get('member_info')
    is_admin = member_info.role in ["creator", "admin"]
    await update.effective_user.send_message("Управление задачами группы:",
                                             reply_markup=task_management_keyboard(is_admin))


async def manage_group_finances(update: Update, context: CallbackContext) -> int:
    member_info = context.user_data.get('member_info')
    is_admin = member_info.role in ["creator", "admin"]
    if member_info.permissions.get('financial', "") == 'expenses' or is_admin:
        fin_info = await get_financial_info(group_oid=context.user_data.get('current_group').group_oid)
        context.user_data['financial'] = fin_info
        await update.effective_user.send_message(f"Финансы группы\n\n{await get_finance_statistics(fin_info)}",
                                                 reply_markup=group_financial_menu(is_admin))
        return ConversationHandler.END
    else:
        await update.effective_user.send_message("У вас нет прав доступа", reply_markup=menu_or_exit())
        return GROUP_MENU_OR_EXIT


async def handle_group_action(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    member_info = context.user_data.get('member_info')
    await query.message.delete()
    if query.data == 'manage_group_info' and member_info.role == "creator":
        await query.message.reply_text("Выберите, что вы хотите изменить:",
                                       reply_markup=edit_group_options_keyboard(True))
        return EDIT_EXISTING_GROUP
    elif query.data == 'manage_group_tasks':
        await manage_group_tasks(update, context)
        return ConversationHandler.END
    elif query.data == 'manage_group_finances':
        return await manage_group_finances(update, context)
    elif query.data == 'manage_group_members' and member_info.role in ["creator", "admin"]:
        await manage_group_members(update, context)
        return MANAGE_MEMBERS
    elif query.data == 'manage_group_admins' and member_info.role == "creator":
        await manage_group_admins(update, context)
        return MANAGE_ADMINS
    return ConversationHandler.END


"""Managing admins"""


async def select_admin(update: Update, context: CallbackContext) -> int:
    selected_option = update.message.text.split(" - ")[0]
    if selected_option.lower() == "назад":
        await context.user_data.get('prev_message').delete()
        await update.message.delete()
        await display_group_info(update, context)
        return SELECT_GROUP_OPTION
    elif selected_option.lower() == "новый админ":
        group = context.user_data['current_group']
        await context.user_data.get('prev_message').delete()
        member_list = [member for member in group.members if member.role not in ('admin', 'creator')]
        context.user_data['member_list'] = member_list
        context.user_data['prev_message'] = await (update.message.
                                                   reply_text("Выберите пользователя для повышения до администратора "
                                                              "(отмена - возврат в меню группы)",
                                                              reply_markup=await member_list_keyboard(member_list)))
        return SELECT_NEW_ADMIN
    try:
        selected_option = int(selected_option)
    except ValueError:
        await update.effective_user.send_message("Неверный ввод! Используйте кнопки из клавиатуры под полем ввода, "
                                                 "или команду /cancel для выхода из режима работы с группой",
                                                 reply_markup=await admin_list_keyboard(context.user_data['admins']))
    selected_admin = next(
        (admin for admin in context.user_data['admins'] if str(admin.member_tid) == selected_option), None)
    context.user_data['selected_admin'] = selected_admin
    await update.message.reply_text("Выберите действие для администратора:",
                                    reply_markup=admin_action_keyboard())
    return ADMIN_ACTION


async def select_new_admin(update: Update, context: CallbackContext) -> int:
    selected_option = update.message.text.split(" - ")[0]
    members = context.user_data['member_list']
    if selected_option == "Назад":
        await update.message.delete()
        await context.user_data.get('prev_message').delete()
        await display_group_info(update, context)
        return SELECT_GROUP_OPTION

    try:
        selected_option = int(selected_option)
    except ValueError:
        await update.effective_user.send_message("Неверный ввод! Используйте кнопки из клавиатуры под полем ввода, "
                                                 "или команду /cancel для выхода из режима работы с группой",
                                                 reply_markup=await member_list_keyboard(members))
        return SELECT_NEW_ADMIN
    selected_member = next(
        (member for member in members if str(member.member_tid) == selected_option),
        None)
    if selected_member:
        group = context.user_data['current_group']
        selected_member.role = 'admin'
        if await set_member_role(group.group_oid, selected_member):
            await update.message.reply_text("Участник успешно назначен администратором.", reply_markup=menu_or_exit())
        else:
            await update.message.reply_text("Не удалось назначить участника администратором.",
                                            reply_markup=menu_or_exit())
    return GROUP_MENU_OR_EXIT


async def handle_admin_action(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "manage_admin_delete":
        group = context.user_data['current_group']
        selected_admin = context.user_data['selected_admin']
        selected_admin.role = 'member'
        if await set_member_role(group.group_oid, selected_admin):
            await query.message.reply_text(f"Роль администратора снята с ({selected_admin.member_tid})",
                                           reply_markup=menu_or_exit())
        else:
            await query.message.reply_text("Не удалось удалить администратора.", reply_markup=menu_or_exit())
        return GROUP_MENU_OR_EXIT
    elif action == "manage_group_goback":
        await context.user_data.get('prev_message').delete()
        await display_group_info(update, context)
        return SELECT_GROUP_OPTION
    return ConversationHandler.END


"""Managing members"""


async def select_member(update: Update, context: CallbackContext) -> int:
    selected_option = update.message.text.split(" - ")[0]
    members = context.user_data['member_list']
    if selected_option.lower() == "назад":
        await update.message.delete()
        await display_group_info(update, context)
        await context.user_data.get('prev_message').delete()
        return SELECT_GROUP_OPTION
    elif selected_option.lower() == "новый":
        msg = await update.effective_user.send_message("Укажите telegram ID пользователя. Он должен быть уже "
                                                       "авторизован "
                                                       "в боте! В ином случае, отправьте ему пригласительную ссылку",
                                                       reply_markup=go_back_kb())
        context.user_data['prev_message'] = msg
        return INPUT_NEW_MEMBER
    try:
        selected_option = int(selected_option)
    except ValueError:
        await update.effective_user.send_message("Неверный ввод! Используйте кнопки из клавиатуры под полем ввода, "
                                                 "или команду /cancel для выхода из режима работы с группой",
                                                 reply_markup=await member_list_keyboard(members))
        return MANAGE_MEMBERS
    selected_member = next(
        (member for member in members if member.member_tid == selected_option), None)
    context.user_data['selected_member'] = selected_member
    await update.message.reply_text("Выберите действие для участника:",
                                    reply_markup=member_action_keyboard(selected_member))
    return MEMBER_ACTION


async def handle_member_action(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    member = context.user_data['selected_member']
    await query.message.delete()
    if action == "manage_member_delete":
        group = context.user_data['current_group']
        group.members = [m for m in group.members if m.member_tid != member.member_tid]
        if await update_group_members(group):
            await query.message.reply_text("Участник успешно удален.", reply_markup=menu_or_exit())
        else:
            await query.message.reply_text("Не удалось удалить участника.", reply_markup=menu_or_exit())
        return GROUP_MENU_OR_EXIT
    elif action == "manage_member_toggle_finance":
        if 'financial' in member.permissions:
            member.permissions.pop('financial')
        else:
            member.permissions['financial'] = "expenses"
        if await update_group_members(context.user_data['current_group']):
            await query.message.reply_text("Права участника обновлены.", reply_markup=menu_or_exit())
        else:
            await query.message.reply_text("Не удалось обновить права участника.", reply_markup=menu_or_exit())
        return GROUP_MENU_OR_EXIT
    elif action == "manage_member_goback":
        await display_group_info(update, context)
        return SELECT_GROUP_OPTION
    return ConversationHandler.END


async def input_new_member_tid(update: Update, context: CallbackContext) -> int:
    if update.message.text.lower() == "назад":
        await update.message.delete()
        await display_group_info(update, context)
        await context.user_data.get('prev_message').delete()
        return SELECT_GROUP_OPTION
    try:
        user_tid = int(update.message.text.strip())
    except ValueError:
        msg = await update.message.reply_text("Неверный формат ввода, попробуйте снова", reply_markup=go_back_kb())
        context.user_data['prev_message'] = msg
        return INPUT_NEW_MEMBER
    user_data = await get_user(user_tid)
    if not user_data:
        await update.message.reply_text("Пользователь не найден. Попробуйте снова или \"Назад\", чтобы вернуться.",
                                        reply_markup=go_back_kb())
        return INPUT_NEW_MEMBER

    new_member = GroupMember(
        role='member',
        permissions={},
        member_oid=user_data.user_oid,
        member_tid=user_data.user_tid
    )
    group = context.user_data['current_group']
    group.members.append(new_member)
    if await add_group_member(group.group_oid, new_member):
        await update.message.reply_text("Новый участник успешно добавлен.", reply_markup=menu_or_exit())
    else:
        await update.message.reply_text("Не удалось добавить нового участника.", reply_markup=menu_or_exit())

    return GROUP_MENU_OR_EXIT


"""Managing tasks"""


async def view_group_tasks(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    group = context.user_data['current_group']
    member_info = context.user_data.get('member_info')
    user_tid = update.effective_user.id

    all_group_tasks = await get_group_tasks(group.group_oid)
    if member_info.role in ["creator", "admin"]:
        group_tasks = all_group_tasks
    else:
        group_tasks = [task for task in all_group_tasks if user_tid in task.assigned_to]
    context.user_data['tasks_selected'] = group_tasks
    if not group_tasks:
        await query.message.reply_text("Задачи не найдены.", reply_markup=ReplyKeyboardRemove())
        # return TASK_MENU_OR_EXIT

    reply_markup = active_tasks_keyboard(group_tasks)
    await query.message.reply_text("Выберите задачу:", reply_markup=reply_markup)
    return SELECT_TASK


async def handle_task_action_selection(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == 'manage_tasks_view':
        return await view_group_tasks(update, context)
    elif action == 'manage_tasks_create':
        return await input_task_assignees(update, context)
    elif action == 'edit_tasks':
        """await edit_tasks(update, context)
        return EDIT_TASKS"""
    return MANAGE_TASKS


"""Managing finances"""


async def create_new_financial(group_oid: str):
    reset_day = datetime.now(timezone.utc).strftime('%d')
    financial = Financial(financial_oid='-',
                          categories=list(),
                          reset_day=reset_day,
                          group_oid=group_oid)
    oid = await create_financial(financial)
    return isinstance(oid, str)


async def handle_new_expense(update, context):
    financial_info = context.user_data['financial']
    categories = financial_info.categories
    context.user_data['add_expenses'] = True
    await update.effective_user.send_message("Выберите категорию для указания расходов",
                                             reply_markup=generate_category_keyboard(categories))
    return SELECT_CATEGORY


async def handle_finance_reset_day(update, context):
    await update.effective_user.send_message("Введите новый день сброса расходов (от 1 до 31). "
                                             "При указании дней 29-31 в месяцах с меньшим числом сброс произойдёт в"
                                             " последний день месяца",
                                             reply_markup=ReplyKeyboardRemove())
    return SET_RESET_DAY


async def send_categories_stats(update: Update, context: CallbackContext, orig_bot_msg: str):
    stats = await get_statistics_by_categories(context)
    is_admin = context.user_data.get('member_info').role in ['admin', 'creator']
    await update.effective_user.send_message(stats, reply_markup=back_or_exit())
    context.user_data['back_message'] = {"text": orig_bot_msg, "reply_markup": group_financial_menu(is_admin)}
    return BACK_OR_EXIT


async def handle_group_financial_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    await query.message.delete()
    if action == 'fin_group_expense':
        return await handle_new_expense(update, context)
    elif action == 'fin_group_stats':
        return await send_categories_stats(update, context, query.message.text)
    elif action == 'fin_group_categories':
        await query.message.reply_text("Выберите действие:", reply_markup=category_menu())
        return CATEGORY_MENU
    elif action == 'fin_group_reset_day':
        return await handle_finance_reset_day(update, context)


"""Creating a group"""


async def group_confirmation_message(update: Update, context: CallbackContext):
    group_data = context.user_data.get("new_group")
    members_list = ', '.join([str(member.member_tid) for member in group_data['members']])
    confirmation_message = (
        f"Подтвердите создание группы:\n"
        f"Название: {group_data['name']}\n"
        f"Описание: {group_data['description']}\n"
        f"Участники: {members_list}"
    )
    await update.message.reply_text(confirmation_message, reply_markup=confirm_or_edit_keyboard())


async def input_group_name(update: Update, context: CallbackContext) -> int:
    group_name = update.message.text
    if context.user_data.get('editing_new_group'):
        context.user_data['new_group']['name'] = group_name
        context.user_data['editing_new_group'] = False
        await group_confirmation_message(update, context)
        return CONFIRM_GROUP_CREATION
    if context.user_data.get('editing_group'):
        context.user_data['current_group'].name = group_name
        if await update_group(context.user_data['current_group']):
            await update.message.reply_text("Название группы изменено", reply_markup=menu_or_exit())
            return GROUP_MENU_OR_EXIT
        else:
            await update.message.reply_text("Не удалось применить изменения. Попробуйте ещё раз позже",
                                            reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

    context.user_data['new_group'] = {'name': group_name}
    await update.message.reply_text("Введите описание для новой группы:", reply_markup=ReplyKeyboardRemove())
    return CREATE_GROUP_DESCRIPTION


async def input_group_description(update: Update, context: CallbackContext) -> int:
    group_description = update.message.text
    if context.user_data.get('editing_group'):
        context.user_data['current_group'].description = group_description
        if await update_group(context.user_data['current_group']):
            await update.message.reply_text("Описание группы изменено", reply_markup=menu_or_exit())
            return GROUP_MENU_OR_EXIT
        else:
            await update.message.reply_text("Не удалось применить изменения. Попробуйте ещё раз позже",
                                            reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    context.user_data['new_group']['description'] = group_description
    if context.user_data.get('editing_new_group'):
        context.user_data['editing_new_group'] = False
        await group_confirmation_message(update, context)
        return CONFIRM_GROUP_CREATION
    kb = ReplyKeyboardMarkup([["Пропустить"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Введите список идентификаторов пользователей (TID), разделённых запятыми,"
                                    " или нажмите 'Пропустить':", reply_markup=kb)
    return ADD_GROUP_MEMBERS


async def form_member_list(member_tids) -> list | int:
    members = []
    for tid in member_tids:
        user_data = await get_user(tid)
        if user_data:
            member = GroupMember(
                role='member',
                permissions={},
                member_oid=user_data.user_oid,
                member_tid=user_data.user_tid
            )
            members.append(member)
        else:
            return tid

    return members


async def input_group_members(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    if user_input.lower() == 'пропустить':
        context.user_data['new_group']['members'] = []
        await group_confirmation_message(update, context)
        return CONFIRM_GROUP_CREATION
    else:
        try:
            member_tids = [int(tid.strip()) for tid in user_input.split(',')]
            members = await form_member_list(member_tids)
            if isinstance(members, int):
                await update.message.reply_text(f"Пользователь с TID {members} не найден. Повторите ввод.")
                return ADD_GROUP_MEMBERS
            context.user_data['new_group']['members'] = members
            await group_confirmation_message(update, context)
            return CONFIRM_GROUP_CREATION
        except ValueError:
            await update.message.reply_text(
                "Неправильный формат. Пожалуйста, введите список идентификаторов пользователей (TID), разделённых запятыми, или нажмите 'Пропустить':")
            return ADD_GROUP_MEMBERS


async def confirm_group_creation(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'group_confirm_yes':
        user_data = context.user_data['user_data-db']
        group_name = context.user_data['new_group']['name']
        group_description = context.user_data['new_group']['description']
        members = context.user_data['new_group']['members']
        creator_member = GroupMember(role='creator', permissions={}, member_oid=user_data.user_oid,
                                     member_tid=user_data.user_tid)
        members.append(creator_member)
        new_group = Group(group_oid='',
                          name=group_name,
                          description=group_description,
                          members=members)

        success, group_oid = await create_group(new_group)
        if success:
            await create_new_financial(group_oid)
            await query.message.reply_text(f"Создана новая группа. Пригласительная ссылка:"
                                           f" {generate_invite_link(group_oid)}")
        else:
            await query.message.reply_text("Не удалось создать группу. Попробуйте снова.")
        reset_group_context(context)
    elif query.data == 'group_confirm_no':
        await query.message.reply_text("Что вы хотите изменить?", reply_markup=edit_group_options_keyboard())
        return EDIT_GROUP
    else:
        await query.message.reply_text("Создание группы отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def generate_invite_link(group_oid: str) -> str:
    return f"{BOT_URL}?start=join_{group_oid}"


async def edit_group_options(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['editing_new_group'] = True
    if query.data == 'edit_group_name':
        await query.message.reply_text("Введите новое название группы:")
        return CREATE_GROUP_NAME
    elif query.data == 'edit_group_description':
        await query.message.reply_text("Введите новое описание группы:")
        return CREATE_GROUP_DESCRIPTION
    elif query.data == 'edit_group_members':
        await query.message.reply_text(
            "Введите список идентификаторов пользователей (TID), разделённых запятыми, или нажмите 'Пропустить':")
        return ADD_GROUP_MEMBERS
    return EDIT_GROUP


async def edit_existing_group_options(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    context.user_data['editing_group'] = True
    if query.data == 'edit_group_name':
        await query.message.reply_text("Введите новое название группы:")
        return CREATE_GROUP_NAME
    elif query.data == 'edit_group_description':
        await query.message.reply_text("Введите новое описание группы:")
        return CREATE_GROUP_DESCRIPTION


async def menu_or_exit_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    if query.data == 'go_to_group_menu':
        context.user_data['editing_group'] = False
        await display_group_info(update, context)
        return SELECT_GROUP_OPTION
    elif query.data == 'go_to_exit':
        reset_group_context(context)
        await query.message.reply_text("Выход из меню группы.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END


group_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(group_selection_callback, pattern=r'^group_')],
    states={
        CREATE_GROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_group_name)],
        CREATE_GROUP_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_group_description)],
        ADD_GROUP_MEMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_group_members)],
        CONFIRM_GROUP_CREATION: [CallbackQueryHandler(confirm_group_creation, pattern=r'^group_confirm')],
        EDIT_GROUP: [CallbackQueryHandler(edit_group_options, pattern=r'^edit_group_')],
        SELECT_GROUP_OPTION: [CallbackQueryHandler(handle_group_action, pattern=r'^manage_group')],
        EDIT_EXISTING_GROUP: [CallbackQueryHandler(edit_existing_group_options, pattern=r'^edit_group')],
        GROUP_MENU_OR_EXIT: [CallbackQueryHandler(menu_or_exit_handler, pattern=r'^go_to_')],
        MANAGE_ADMINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_admin)],
        ADMIN_ACTION: [CallbackQueryHandler(handle_admin_action, pattern=r'^manage_admin_')],
        SELECT_NEW_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_new_admin)],
        MANAGE_MEMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_member)],
        MEMBER_ACTION: [CallbackQueryHandler(handle_member_action, pattern=r'^manage_member_')],
        INPUT_NEW_MEMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_new_member_tid)],
        # MANAGE_TASKS: [CallbackQueryHandler(handle_task_action_selection, pattern=r'^manage_tasks_')],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

(SELECT_TASK, CREATE_TASK_NAME, CREATE_TASK_DESCRIPTION, CREATE_TASK_DEADLINE, CREATE_TASK_RECURRING,
 CONFIRM_TASK_CREATION, SELECT_EDIT_OPTION, HANDLE_TASK_ACTION, CONFIRM_TASK_EDIT, SELECT_TASK_ASSIGNEES) = range(10)


async def input_task_assignees(update: Update, context: CallbackContext) -> int:
    group = context.user_data['current_group']
    member_list = [member for member in group.members]
    context.user_data['member_list'] = member_list
    context.user_data['task_assignees'] = list()
    context.user_data['task_assignee_names'] = list()
    reply_markup = await member_list_keyboard(member_list, confirm=True)
    await update.effective_user.send_message("Выберите пользователей для назначения задачи (по одному):",
                                             reply_markup=reply_markup)
    return SELECT_TASK_ASSIGNEES


async def proceed_with_assignees(update: Update, context: CallbackContext):
    if context.user_data.get('editing_new_task'):
        context.user_data['editing_new_task'] = False
        retval = await confirm_task_creation(update, context)
        return retval
    if not context.user_data.get('task_assignees') or len(context.user_data.get('task_assignees')) == 0:
        await update.effective_user.send_message("Не выбрано ни одного пользователя. Выберите хотя бы одного, "
                                                 "или отмените операцию (/cancel)", )
        return SELECT_TASK_ASSIGNEES
    await update.effective_user.send_message("Введите название новой задачи:",
                                             reply_markup=ReplyKeyboardRemove())
    return CREATE_TASK_NAME


async def handle_task_assignee_selection(update: Update, context: CallbackContext) -> int:
    selected_option = update.message.text.split(" - ")[0]
    if selected_option.lower() == "готово":
        return await proceed_with_assignees(update, context)
    try:
        selected_option = int(selected_option)
    except ValueError:
        await update.message.reply_text("Неверный ввод! Используйте кнопки из клавиатуры под полем ввода.")
        return SELECT_TASK_ASSIGNEES

    selected_member = next(
        (member for member in context.user_data['member_list'] if member.member_tid == selected_option), None)
    if not selected_member:
        await update.message.reply_text("Участник не найден, попробуйте снова.")
        return SELECT_TASK_ASSIGNEES
    context.user_data.get('task_assignees', []).append(selected_member)
    try:
        name = update.message.text.split(" - ")[1]
        context.user_data.get('task_assignee_names', []).append(name)
        context.user_data['member_list'] = [member for member in context.user_data['member_list'] if
                                            member.member_tid != selected_option]
        await update.message.reply_text(f"Участник {selected_member.member_tid} добавлен. Выберите ещё "
                                        f"одного или нажмите 'Готово' для завершения.",
                                        reply_markup=await member_list_keyboard(context.user_data['member_list'], True))
        return SELECT_TASK_ASSIGNEES
    except IndexError:
        await update.message.reply_text("Неверный ввод! Используйте кнопки из клавиатуры под полем ввода.")
        return SELECT_TASK_ASSIGNEES


group_task_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_task_action_selection, pattern=r'^manage_tasks_')],
    states={
        SELECT_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_task)],
        CREATE_TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_name)],
        CREATE_TASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_description)],
        CREATE_TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_deadline)],
        CREATE_TASK_RECURRING: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_recurring)],
        CONFIRM_TASK_CREATION: [CallbackQueryHandler(handle_confirmation, pattern=r'^task_confirm')],
        SELECT_EDIT_OPTION: [CallbackQueryHandler(handle_edit_option, pattern=r'^task_edit')],
        HANDLE_TASK_ACTION: [CallbackQueryHandler(handle_task_action, pattern=r'^task_action_')],
        CONFIRM_TASK_EDIT: [CallbackQueryHandler(handle_edit_confirmation, pattern=r'^task_confirm')],
        SELECT_TASK_ASSIGNEES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_assignee_selection)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

(CHOOSE_EXPENSE_CATEGORY, SET_RESET_DAY, CATEGORY_NAME, CATEGORY_DESCRIPTION, CATEGORY_BUDGET_LIMIT,
 CONFIRM_CATEGORY_CREATION, CATEGORY_MENU, SELECT_FIN_EDIT_OPTION, SELECT_CATEGORY, CONFIRM_CATEGORY_EDIT
 , INPUT_EXPENSE_AMOUNT, INPUT_EXPENSE_DESCRIPTION, CONFIRM_EXPENSE_CREATION, BACK_OR_EXIT) = range(14)


async def back_or_exit_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    await query.message.delete()
    if action == 'back':
        message = context.user_data.get('back_message', {"text": "Возвращаю назад"})
        previous_state = context.user_data.get('previous_state', ConversationHandler.END)
        await update.effective_user.send_message(text=message.get('text'), reply_markup=message.get('reply_markup'))
        return previous_state
    elif action == 'exit':
        context.user_data.clear()
        await query.message.reply_text("Вы завершили взаимодействие и вернулись в главное меню.")
        return ConversationHandler.END


group_financial_conversation_manager = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_group_financial_menu, pattern=r'^fin_group')],
    states={
        SET_RESET_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_reset_day)],
        CATEGORY_MENU: [CallbackQueryHandler(category_menu_callback, pattern=r'^(create_category|edit_categories)$')],
        CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_category_name)],
        CATEGORY_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_category_description)],
        CATEGORY_BUDGET_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_category_budget_limit)],
        CONFIRM_CATEGORY_CREATION: [CallbackQueryHandler(handle_category_confirm, pattern=r'^fin_confirm')],
        SELECT_FIN_EDIT_OPTION: [CallbackQueryHandler(handle_edit_fin_option, pattern=r'^fin_edit_')],
        CONFIRM_CATEGORY_EDIT: [CallbackQueryHandler(handle_category_edit_confirm, pattern=r'^fin_confirm')],
        SELECT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_category)],
        INPUT_EXPENSE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_expense_description)],
        INPUT_EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_expense_amount)],
        CONFIRM_EXPENSE_CREATION: [CallbackQueryHandler(handle_expense_confirm, pattern=r'^expense_confirm')],
        BACK_OR_EXIT: [CallbackQueryHandler(back_or_exit_handler, pattern=r'^(back|exit)$')]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
