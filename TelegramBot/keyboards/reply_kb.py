from dateutil.parser import isoparse
from telegram import ReplyKeyboardMarkup

from TelegramBot.models import Category


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
