from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

from TelegramBot.keyboards.inline_kb import notifications_keyboard
from TelegramBot.utils.api import update_user_notifications


async def notifications_command(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Выберите настройки уведомлений:", reply_markup=notifications_keyboard())
    return ConversationHandler.END


async def handle_notifications_selection(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    selection = query.data
    if selection == 'notify_all':
        context.user_data['notifications'] = 'all'
        await update_user_notifications(user_id, 'all')
        await query.message.reply_text("Вы настроили получение всех уведомлений.")
    elif selection == 'notify_day_before':
        context.user_data['notifications'] = 'day_before'
        await update_user_notifications(user_id, 'day_before')
        await query.message.reply_text("Вы настроили получение уведомлений за день до дедлайна.")
    elif selection == 'notify_off':
        context.user_data['notifications'] = 'off'
        await update_user_notifications(user_id, 'off')
        await query.message.reply_text("Вы отключили все уведомления.")

    return ConversationHandler.END

