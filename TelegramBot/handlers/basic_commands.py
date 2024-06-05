from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from ..utils.api import check_and_create_user
from ..utils.states import reset_financial_context


async def start_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_tid = user.id
    user_name = user.full_name

    if await check_and_create_user(user_tid, user_name):
        await update.message.reply_text(f"Welcome, {user_name}!")
    else:
        await update.message.reply_text("Failed to register user. Please try again later.")


async def help_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user

    help_text = (
        "Here are the available commands:\n"
        "/start - Начало работы\n"
        "/help - Помощь (текущая команда)\n"
        # Add other commands as needed
    )
    await update.message.reply_text(help_text)


async def cancel(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    context.user_data.pop('new_task', None)
    context.user_data.pop('editing_new_task', None)
    context.user_data.pop('editing_task', None)
    context.user_data.pop('tasks', None)
    context.user_data.pop('tasks_selected', None)
    context.user_data.pop('current_task', None)

    reset_financial_context(context)

    await update.message.reply_text(f"Отмена операции.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END