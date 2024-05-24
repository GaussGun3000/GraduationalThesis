import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from TelegramBot.config import BOT_TOKEN
from TelegramBot.handlers.basic_commands import start_command

logging.basicConfig(level=logging.INFO)


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))

    application.run_polling()


if __name__ == "__main__":
    main()
