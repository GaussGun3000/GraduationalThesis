from telegram.ext import CallbackContext


def reset_financial_context(context: CallbackContext):
    keys_to_remove = [
        'financial',
        'new_category',
        'selected_category',
        'editing_category',
        'edited_category',
        'add_expenses',
        'new_expense',
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
