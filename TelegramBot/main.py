import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler
from TelegramBot.config import BOT_TOKEN
from TelegramBot.handlers.basic_commands import start_command, help_command
from TelegramBot.handlers.financial import finance_command, financial_conversation_handler
from TelegramBot.handlers.group import group_command, group_conversation_handler, group_task_conversation_handler, \
    group_financial_conversation_manager
from TelegramBot.handlers.task import (task_command, task_main_menu_callback, task_conversation_handler,)
from TelegramBot.utils.states import error_handler

logging.basicConfig(level=logging.INFO)


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("task", task_command))
    application.add_handler(CommandHandler("finance", finance_command))
    application.add_handler(CommandHandler("group", group_command))
    application.add_handler(task_conversation_handler)
    application.add_handler(financial_conversation_handler)
    application.add_handler(group_conversation_handler)
    application.add_handler(group_task_conversation_handler)
    application.add_handler(group_financial_conversation_manager)
    application.add_error_handler(error_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
