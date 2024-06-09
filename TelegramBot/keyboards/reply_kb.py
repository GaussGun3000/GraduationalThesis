from dateutil.parser import isoparse
from telegram import ReplyKeyboardMarkup

from TelegramBot.models import Category
from TelegramBot.utils.api import get_user


def active_tasks_keyboard(active_tasks):
    keyboard = []
    for index, task in enumerate(active_tasks):
        task_label = f"{index + 1} - {task.title} - {isoparse(task.deadline).strftime('%d.%m %H:%M')}"
        keyboard.append([task_label])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def recurring_keyboard():
    keyboard = [
        ["Разовая", "Ежедневно"],
        ["Еженедельно", "Ежемесячно"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def confirmation_keyboard():
    keyboard = [
        ["Да", "Нет"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def generate_category_keyboard(categories: list[Category]):
    keyboard = []
    for index, category in enumerate(categories):
        keyboard.append([f"{index + 1} - {category.name} ({category.budget_limit})"])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


async def admin_list_keyboard(admins: list):
    admin_names = list()
    for admin in admins:
        admin_info = await get_user(admin.member_tid)
        admin_name = f"{admin_info.user_tid} - {admin_info.name}"
        admin_names.append(admin_name)
    admin_keyboard = [["Назад", "Новый админ"]] + [[name] for name in admin_names]
    return ReplyKeyboardMarkup(admin_keyboard, one_time_keyboard=True, resize_keyboard=True)


async def member_list_keyboard(members: list, confirm=False):
    member_names = list()
    for member in members:
        member_info = await get_user(member.member_tid)
        admin_name = f"{member_info.user_tid} - {member_info.name}"
        member_names.append(admin_name)
    actions = ["Назад", "Новый"] if not confirm else ["Готово"]
    admin_keyboard = [actions] + [[name] for name in member_names]
    return ReplyKeyboardMarkup(admin_keyboard, one_time_keyboard=True, resize_keyboard=True)


def go_back_kb():
    return ReplyKeyboardMarkup([["Назад"]], one_time_keyboard=True, resize_keyboard=True)