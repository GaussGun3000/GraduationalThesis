from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..models import Task, User
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


def edit_task_options_keyboard(group_task=False):
    keyboard = [
        [InlineKeyboardButton("Название", callback_data='task_edit_title')],
        [InlineKeyboardButton("Описание", callback_data='task_edit_description')],
        [InlineKeyboardButton("Дедлайн", callback_data='task_edit_deadline')],
        [InlineKeyboardButton("Периодичность", callback_data='task_edit_recurring')],
    ]
    if group_task:
        keyboard += [InlineKeyboardButton("Назначение", callback_data='task_edit_assignees')],
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


def select_group_keyboard(user: User, created_group, user_groups):
    keyboard = []
    if created_group or user.is_premium():
        keyboard.append([InlineKeyboardButton("Моя группа", callback_data=f"group_my")])

    for group in user_groups:
        keyboard.append([InlineKeyboardButton(group['name'], callback_data=f"group_{group['id']}")])

    return InlineKeyboardMarkup(keyboard)


def confirm_or_edit_keyboard():
    inline_keyboard = [
        [InlineKeyboardButton("Подтвердить", callback_data='group_confirm_yes')],
        [InlineKeyboardButton("Редактировать", callback_data='group_confirm_no')],
    ]
    return InlineKeyboardMarkup(inline_keyboard)


def edit_group_options_keyboard(existing: bool = False):
    inline_keyboard = [
        [InlineKeyboardButton("Название", callback_data='edit_group_name')],
        [InlineKeyboardButton("Описание", callback_data='edit_group_description')],
    ]
    if not existing:
        inline_keyboard += [InlineKeyboardButton("Участники", callback_data='edit_group_members')],
    return InlineKeyboardMarkup(inline_keyboard)


def menu_or_exit():
    inline_keyboard = [
        [InlineKeyboardButton("В меню группы", callback_data='go_to_group_menu')],
        [InlineKeyboardButton("Завершить", callback_data='go_to_exit')],
    ]
    return InlineKeyboardMarkup(inline_keyboard)


def group_actions(member_role: str):
    role_map = {
        "creator": [[InlineKeyboardButton("Редактировать группу", callback_data='manage_group_info')],
                    [InlineKeyboardButton("Администраторы", callback_data='manage_group_admins')],
                    [InlineKeyboardButton("Участники", callback_data='manage_group_members')]],
        "admin": [[InlineKeyboardButton("Участники", callback_data='manage_group_members')]],
        "member": []
        }
    keyboard = [
        [InlineKeyboardButton("Задачи", callback_data='manage_group_tasks')],
        [InlineKeyboardButton("Финансы", callback_data='manage_group_finances')],
    ] + role_map.get(member_role)
    return InlineKeyboardMarkup(keyboard)


def admin_action_keyboard():
    keyboard = [
        [InlineKeyboardButton("Удалить из администраторов", callback_data='manage_admin_delete')],
        [InlineKeyboardButton("Назад к меню группы", callback_data='manage_admin_goback')]
    ]
    return InlineKeyboardMarkup(keyboard)


def member_action_keyboard(member):
    permission_button_text = "➕доступ к финансам" if member.permissions.get('financial') not in ("expenses",) else\
        "⛔доступ к финансам"
    keyboard = [
        [InlineKeyboardButton("Удалить", callback_data='manage_member_delete')],
        [InlineKeyboardButton(permission_button_text, callback_data='manage_member_toggle_finance')],
        [InlineKeyboardButton("Назад к меню группы", callback_data='manage_member_goback')]
    ]
    return InlineKeyboardMarkup(keyboard)


def task_management_keyboard(is_admin: bool):
    keyboard = [
        [InlineKeyboardButton("Просмотреть задачи", callback_data='manage_tasks_view')],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("Создать групповую", callback_data='manage_tasks_create')])
    return InlineKeyboardMarkup(keyboard)


