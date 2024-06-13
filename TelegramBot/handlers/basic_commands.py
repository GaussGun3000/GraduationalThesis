from datetime import datetime, timezone

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler

from ..keyboards.inline_kb import main_menu
from ..models import GroupMember, User
from ..utils.api import check_and_create_user, create_user, get_user, get_group, add_group_member
from ..utils.states import reset_financial_context, reset_group_context, reset_task_context, reset_all_context


async def start_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_tid = user.id
    user_name = user.full_name + " " + user.name if user.name else ""

    args = context.args
    if args and args[0].startswith("join_"):
        group_oid = args[0].split("_")[1]
        await join_group_by_link(update, context, group_oid)
        return

    if await check_and_create_user(user_tid, user_name):
        await update.message.reply_text(f"Добро пожаловать, {user_name}!\n\n"
                                        f"Инструкция доступна по команде /help. Или если всё знакомо, можно сразу "
                                        f"начинать пользоваться", reply_markup=main_menu())
    else:
        await update.message.reply_text("Не удалось вас зарегистрировать. Попробуйте команду /start ещё раз")


async def help_command(update: Update, context: CallbackContext) -> None:
    reset_all_context(context)
    user = update.effective_user

    help_text = (
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/help - Помощь (текущая команда)\n"
        "/task - просмотр \\ управление задачами\n"
        "/finance - просмотр \\ управление финансами\n"
        "/group - просмотр \\ управление группами\n\n"
        "Если нужно отменить действие, или же что-то зависло - можно всегда вернуться в главное меню по команде "
        "/cancel.\n\n*Все команды в тексте этого меню - кликабельны*"
    )
    await update.message.reply_text(help_text, reply_markup=main_menu(), parse_mode='Markdown')


async def join_group_by_link(update: Update, context: CallbackContext, group_oid: str) -> None:
    user_tid = update.effective_user.id
    group = await get_group(group_oid)
    if not group:
        await update.message.reply_text("Группа не найдена или ссылка недействительна.")
        return

    user_data = await get_user(user_tid)
    if not user_data:
        current_date = datetime.now(timezone.utc).isoformat()
        user_name = update.effective_user.full_name + " " + update.effective_user.name if update.effective_user.name else ""
        user = User("", user_tid, user_name, "", "free", current_date, "", current_date)
        response = await create_user(user.to_request_dict())
        if response.status != 201:
            await update.message.reply_text("Ошибка с данными пользователя. Попробуйте ещё раз позже")
            return
        data = await response.json()
        user_oid = data.get('user_oid')
    else:
        user_oid = user_data.user_oid

    new_member = GroupMember(role='member', permissions={}, member_oid=user_oid, member_tid=user_tid)
    success = await add_group_member(group_oid, new_member)
    if success:
        await update.message.reply_text(f"Вы успешно присоединились к группе '{group.name}'")
    else:
        await update.message.reply_text("Не удалось присоединиться к группе. Попробуйте снова.")


async def cancel(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    reset_task_context(context)
    reset_financial_context(context)
    reset_group_context(context)
    await update.message.reply_text(f"Отмена операции.", reply_markup=main_menu())
    return ConversationHandler.END