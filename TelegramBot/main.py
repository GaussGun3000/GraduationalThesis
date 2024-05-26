import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from TelegramBot.config import BOT_TOKEN
from TelegramBot.handlers.basic_commands import start_command, help_command
from TelegramBot.handlers.task import task_command

logging.basicConfig(level=logging.INFO)


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("task", task_command))

    application.run_polling()


if __name__ == "__main__":
    main()
