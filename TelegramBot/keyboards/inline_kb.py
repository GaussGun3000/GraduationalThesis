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
    buttons = [[InlineKeyboardButton("Выполнена", callback_data=f'complete_{task.task_oid}')]]

    if not task.group_oid:  # personal
        buttons.append([InlineKeyboardButton("Редактировать", callback_data=f'edit_{task.task_oid}')])
        buttons.append([InlineKeyboardButton("Удалить", callback_data=f'delete_{task.task_oid}')])
    else:  # group
        if api.is_group_admin(user_id, task.group_oid):
            buttons.append([InlineKeyboardButton("Редактировать", callback_data=f'edit_{task.task_oid}')])
            buttons.append([InlineKeyboardButton("Удалить", callback_data=f'delete_{task.task_oid}')])

    return InlineKeyboardMarkup(buttons)
