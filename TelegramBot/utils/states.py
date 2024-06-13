from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler


def reset_financial_context(context: CallbackContext):
    keys_to_remove = [
        'financial',
        'new_category',
        'selected_category',
        'editing_category',
        'edited_category',
        'add_expenses',
        'new_expense',
        'back_message',
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)


def reset_group_context(context: CallbackContext):
    keys_to_remove = [
        'new_group',
        'my_group',
        'user_data-db',
        'editing_new_group',
        'current_group',
        'member_info',
        'editing_group',
        'admins',
        'current_admin',
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)


def reset_task_context(context: CallbackContext):
    keys_to_remove = [
        'new_task'
        'editing_new_task',
        'editing_task',
        'tasks',
        'tasks_selected',
        'current_task',
        'task_assignee_names',
        'task_assignees'
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)


async def error_handler(update: Update, context: CallbackContext) -> int:
    context.user_data.clear()

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.message.delete()
        except telegram.error.BadRequest:
            pass
        await update.effective_user.send_message("Что-то пошло не так. Вы вернулись в главное меню.")
    else:
        await update.message.reply_text("Что-то пошло не так. Вы вернулись в главное меню.")

    return ConversationHandler.END


def reset_all_context(context):
    reset_financial_context(context)
    reset_group_context(context)
    reset_task_context(context)
