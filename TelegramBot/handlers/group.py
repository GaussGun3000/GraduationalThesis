from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, Message
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, CommandHandler, filters, \
    CallbackQueryHandler

from .basic_commands import cancel
from ..utils.api import get_user_tasks, update_task, create_task, get_user, delete_task, get_financial_info, \
    create_financial, update_reset_day, create_category, update_category, create_expense, get_group, create_group, \
    get_user_groups, get_created_group, add_group_member, create_user, update_group, set_member_role
from datetime import datetime, timezone, timedelta
from dateutil.parser import isoparse
from ..keyboards.reply_kb import active_tasks_keyboard, recurring_keyboard, generate_category_keyboard, \
    admin_list_keyboard, member_list_keyboard
from ..keyboards.inline_kb import financial_menu, category_menu, fin_confirmation_keyboard, edit_fin_options_keyboard, \
    expense_confirmation_keyboard, select_group_keyboard, confirm_or_edit_keyboard, edit_group_options_keyboard, \
    group_actions, menu_or_exit, admin_action_keyboard
from ..models import Group, GroupMember, User
from ..utils.states import reset_financial_context, reset_group_context
from ..config import BOT_URL

(CREATE_GROUP_NAME, CREATE_GROUP_DESCRIPTION, ADD_GROUP_MEMBERS, CONFIRM_GROUP_CREATION, EDIT_GROUP,
 EDIT_EXISTING_GROUP, SELECT_GROUP_OPTION, TASK_MENU_OR_EXIT, MANAGE_ADMINS, ADMIN_ACTION, SELECT_NEW_ADMIN,
 ) = range(11)


async def group_command(update: Update, context: CallbackContext) -> None:
    reset_group_context(context)
    user_tid = update.effective_user.id
    created_group = await get_created_group(user_tid)
    user_groups = await get_user_groups(user_tid)
    user_data = await get_user(user_tid)
    context.user_data['user_data-db'] = user_data
    if created_group:
        context.user_data['my_group'] = created_group
    if not created_group and not user_groups and not user_data.is_premium():
        await update.message.reply_text("Вы не состоите в группах и у вас нет премиума для создания группы.")
        return

    await update.message.reply_text("Выберите группу для управления:",
                                    reply_markup=select_group_keyboard(user_data, created_group, user_groups))


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
        #  логикa для работы с выбранной группой.
        return ConversationHandler.END


async def manage_group_admins(update: Update, context: CallbackContext):
    group = context.user_data['current_group']
    admin_list = [member for member in group.members if member.role == 'admin']
    context.user_data['admins'] = admin_list
    msg = await update.effective_user.send_message("Выберите администратора для изменений, или \"Новый админ\", чтобы "
                                                   "выбрать нового, или \"Назад\", чтобы вернутся в предыдущее меню",
                                                   reply_markup=await admin_list_keyboard(admin_list))
    context.bot_data['prev_message'] = msg


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
        await query.message.reply_text("Управление задачами группы: функция в разработке.")
        return ConversationHandler.END
    elif query.data == 'manage_group_finances':
        await query.message.reply_text("Управление финансами группы: функция в разработке.")
        return ConversationHandler.END
    elif query.data == 'manage_group_members' and member_info.role in ["creator", "admin"]:
        await query.message.reply_text("Управление участниками группы: функция в разработке.")
        return ConversationHandler.END
    elif query.data == 'manage_group_admins' and member_info.role == "creator":
        await manage_group_admins(update, context)
        return MANAGE_ADMINS
    return ConversationHandler.END


"""Managing admins"""


async def select_admin(update: Update, context: CallbackContext) -> int:
    selected_option = update.message.text.split(" - ")[0]
    if selected_option.lower() == "назад":
        await context.bot_data.get('prev_message').delete()
        await update.message.delete()
        await display_group_info(update, context)
        return SELECT_GROUP_OPTION
    elif selected_option.lower() == "новый админ":
        group = context.user_data['current_group']
        await context.bot_data.get('prev_message').delete()
        member_list = [member for member in group.members if member.role not in ('admin', 'creator')]
        context.bot_data['prev_message'] = await (update.message.
                                                  reply_text("Выберите пользователя для повышения до администратора "
                                                             "(отмена - возврат в меню группы)",
                                                             reply_markup=await member_list_keyboard(member_list)))
        return SELECT_NEW_ADMIN
    selected_admin = next(
        (admin for admin in context.user_data['admins'] if str(admin.member_tid) == selected_option), None)
    context.user_data['selected_admin'] = selected_admin
    await update.message.reply_text("Выберите действие для администратора:",
                                    reply_markup=admin_action_keyboard())
    return ADMIN_ACTION


async def select_new_admin(update: Update, context: CallbackContext) -> int:
    selected_option = update.message.text.split(" - ")[0]
    if selected_option == "Назад":
        await context.bot_data.get('prev_message').delete()
        await display_group_info(update, context)
        return SELECT_GROUP_OPTION

    selected_member = next(
        (member for member in context.user_data['current_group'].members if str(member.member_tid) == selected_option),
        None)
    if selected_member:
        group = context.user_data['current_group']
        selected_member.role = 'admin'
        if await set_member_role(group.group_oid, selected_member):
            await update.message.reply_text("Участник успешно назначен администратором.", reply_markup=menu_or_exit())
        else:
            await update.message.reply_text("Не удалось назначить участника администратором.",
                                            reply_markup=menu_or_exit())
    return TASK_MENU_OR_EXIT


async def handle_admin_action(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "manage_admin_delete":
        group = context.user_data['current_group']
        selected_admin = context.user_data['selected_admin']
        selected_admin.role = 'member'
        if await set_member_role(group.group_oid, selected_admin):
            await query.message.reply_text(f"Роль администратора снята с ({selected_admin.member_tid})", reply_markup=menu_or_exit())
        else:
            await query.message.reply_text("Не удалось удалить администратора.", reply_markup=menu_or_exit())
        return TASK_MENU_OR_EXIT
    elif action == "manage_group_goback":
        await context.bot_data.get('prev_message').delete()
        await display_group_info(update, context)
        return SELECT_GROUP_OPTION
    return ConversationHandler.END


"""Managing members"""






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
            return TASK_MENU_OR_EXIT
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
            return TASK_MENU_OR_EXIT
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
        new_group = Group(
            group_oid='',
            name=group_name,
            description=group_description,
            members=members
        )
        success, group_oid = await create_group(new_group)
        if success:
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


async def generate_invite_link(group_oid: str) -> str:
    return f"https://{BOT_URL}/join?group={group_oid}"


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


async def join_group(update: Update, context: CallbackContext) -> None:
    user_tid = update.effective_user.id
    group_oid = context.args[0]
    group = await get_group(group_oid)
    if not group:
        await update.message.reply_text("Группа не найдена или ссылка недействительна.")
        return
    user_data = await get_user(user_tid)
    if not user_data:
        current_date = datetime.now(timezone.utc).isoformat()
        user = User("", user_tid, update.effective_user.name, "", "free", current_date, "", current_date)
        response = await create_user(user.to_request_dict())
        if response.status != 201:
            await update.message.reply_text("Ошибка с данными пользователя. Попробуйте ещё раз позже")
            return
        data = await response.json()
        user_oid = data.get('user_oid')
    user_oid = user_data.user_oid
    new_member = GroupMember(
        role='member',
        permissions={},
        member_oid=user_oid,
        member_tid=user_tid)
    success = await add_group_member(group_oid, new_member)
    if success:
        await update.message.reply_text(f"Вы успешно присоединились к группе '{group.name}'")
    else:
        await update.message.reply_text("Не удалось присоединиться к группе. Попробуйте снова.")


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
        TASK_MENU_OR_EXIT: [CallbackQueryHandler(menu_or_exit_handler, pattern=r'^go_to_')],
        MANAGE_ADMINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_admin)],
        ADMIN_ACTION: [CallbackQueryHandler(handle_admin_action, pattern=r'^manage_admin_')],
        SELECT_NEW_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_new_admin)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
