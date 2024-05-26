from telegram import Update
from telegram.ext import CallbackContext
from ..utils.api import check_and_create_user


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
