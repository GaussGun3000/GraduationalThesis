def create_active_tasks_keyboard(active_tasks):
    keyboard = []
    for index, task in enumerate(active_tasks):
        task_label = f"{index + 1} - {task['title']} - {task['deadline'][:10]}"
        keyboard.append([task_label])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)