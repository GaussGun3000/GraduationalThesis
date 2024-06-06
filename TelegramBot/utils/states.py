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


def reset_group_context(context: CallbackContext):
    keys_to_remove = [
        'new_group',
        'my_group',
        'user_data-db',
        'editing_new_group',
        'current_group',
        'member_info',
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
