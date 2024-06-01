from telegram import ReplyKeyboardMarkup


def active_tasks_keyboard(active_tasks):
    keyboard = []
    for index, task in enumerate(active_tasks):
        task_label = f"{index + 1} - {task.title} - {task.deadline[:10]}"
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