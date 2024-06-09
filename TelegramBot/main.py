import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dateutil.parser import isoparse
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler
from TelegramBot.config import BOT_TOKEN
from TelegramBot.handlers.basic_commands import start_command, help_command
from TelegramBot.handlers.financial import finance_command, financial_conversation_handler
from TelegramBot.handlers.group import group_command, group_conversation_handler, group_task_conversation_handler, \
    group_financial_conversation_manager
from TelegramBot.handlers.notification import notifications_command, handle_notifications_selection
from TelegramBot.handlers.task import (task_command, task_main_menu_callback, task_conversation_handler,)
from TelegramBot.utils.api import get_active_tasks, update_task, get_user_by_oid
from TelegramBot.utils.states import error_handler

logging.basicConfig(level=logging.INFO)
application = ApplicationBuilder().token(BOT_TOKEN).build()


async def send_task_notifications():
    tasks = await get_active_tasks()
    print("checked tasks")
    for task in tasks:
        deadline = isoparse(task.deadline)
        now = datetime.now(timezone.utc)
        delta = deadline - now
        days = delta.days

        if delta.days <= 1 and not task.notified["day_before"]:
            await notify_users(task, "day_before")
            task.notified["day_before"] = True
            task.notified["week_before"] = True
            await update_task(task)
            return

        if delta.days <= 7 and not task.notified["week_before"]:
            await notify_users(task, "week_before")
            task.notified["week_before"] = True
            await update_task(task)


async def notify_users(task, when):
    message = (f"Дедлайн {isoparse(task.deadline).strftime('%d.%m.%Y %H:%M')} ({task.title})\n\nНужно сделать:\n"
               f"{task.description}")
    # if when == "week_before":
    #     message += "Осталась одна неделя до дедлайна."
    # elif when == "day_before":
    #     message += "Остался один день до дедлайна."
    for user_oid in task.assigned_to:
        user = await get_user_by_oid(user_oid)
        if user and user.notification_settings.get("notifications", "") in ('all', when):
            await application.bot.send_message(chat_id=user.user_tid, text=message)


def main():
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("task", task_command))
    application.add_handler(CommandHandler("finance", finance_command))
    application.add_handler(CommandHandler("group", group_command))
    application.add_handler(CommandHandler("notifications", notifications_command))
    application.add_handler(CallbackQueryHandler(handle_notifications_selection, ))
    application.add_handler(task_conversation_handler)
    application.add_handler(financial_conversation_handler)
    application.add_handler(group_conversation_handler)
    application.add_handler(group_task_conversation_handler)
    application.add_handler(group_financial_conversation_manager)
    application.add_error_handler(error_handler)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_task_notifications, 'interval', minutes=5)
    scheduler.start()
    application.run_polling()


if __name__ == "__main__":
    main()
