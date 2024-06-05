from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..models import Task
from ..utils import api


def task_menu():
    inline_keyboard = [
        [InlineKeyboardButton("Новая", callback_data='new_task')],

        [InlineKeyboardButton("Активные", callback_data='active_tasks'),
         InlineKeyboardButton("Личные", callback_data='personal_tasks'),
         InlineKeyboardButton("Архив", callback_data='archive_tasks')],
    ]
    return InlineKeyboardMarkup(inline_keyboard)


def task_action_buttons(task: Task, user_id: int):
    buttons = [[InlineKeyboardButton("Выполнена", callback_data=f'task_action_complete')]]

    if not task.group_oid:  # personal
        buttons.append([InlineKeyboardButton("Редактировать", callback_data=f'task_action_edit')])
        buttons.append([InlineKeyboardButton("Удалить", callback_data=f'task_action_delete')])
    else:  # group
        if api.is_group_admin(user_id, task.group_oid):
            buttons.append([InlineKeyboardButton("Редактировать", callback_data=f'task_action_edit')])
            buttons.append([InlineKeyboardButton("Удалить", callback_data=f'task_action_delete')])

    return InlineKeyboardMarkup(buttons)


def confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton("Да", callback_data='task_confirm_yes')],
        [InlineKeyboardButton("Изменить", callback_data='task_confirm_edit')]
    ]
    return InlineKeyboardMarkup(keyboard)


def fin_confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton("Да", callback_data='fin_confirm_yes')],
        [InlineKeyboardButton("Изменить", callback_data='fin_confirm_edit')]
    ]
    return InlineKeyboardMarkup(keyboard)


def expense_confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton("Подтвердить", callback_data='expense_confirm_yes')],
        [InlineKeyboardButton("Ввести заново", callback_data='expense_confirm_edit')]
    ]
    return InlineKeyboardMarkup(keyboard)


def edit_task_options_keyboard():
    keyboard = [
        [InlineKeyboardButton("Название", callback_data='task_edit_title')],
        [InlineKeyboardButton("Описание", callback_data='task_edit_description')],
        [InlineKeyboardButton("Дедлайн", callback_data='task_edit_deadline')],
        [InlineKeyboardButton("Периодичность", callback_data='task_edit_recurring')]
    ]
    return InlineKeyboardMarkup(keyboard)


def edit_fin_options_keyboard():
    keyboard = [
        [InlineKeyboardButton("Название", callback_data='fin_edit_title')],
        [InlineKeyboardButton("Описание", callback_data='fin_edit_description')],
        [InlineKeyboardButton("Лимит", callback_data='fin_edit_limit')],
    ]
    return InlineKeyboardMarkup(keyboard)


def financial_menu():
    inline_keyboard = [
        [InlineKeyboardButton("Статистика", callback_data='finance_stats')],
        [InlineKeyboardButton("Расход", callback_data='finance_expense')],
        [InlineKeyboardButton("Категории", callback_data='finance_categories')],
        [InlineKeyboardButton("День сброса", callback_data='finance_reset_day')],
    ]
    return InlineKeyboardMarkup(inline_keyboard)


def category_menu():
    inline_keyboard = [
        [InlineKeyboardButton("Создать новую категорию", callback_data='create_category')],
        [InlineKeyboardButton("Редактировать категории", callback_data='edit_categories')],
    ]
    return InlineKeyboardMarkup(inline_keyboard)