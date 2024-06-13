import re
from telegram import Update, ReplyKeyboardRemove, Message
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, CommandHandler, filters, \
    CallbackQueryHandler

from .basic_commands import cancel
from ..utils.api import get_user, delete_task, get_financial_info, \
    create_financial, update_reset_day, create_category, update_category, create_expense
from datetime import datetime, timezone, timedelta
from ..keyboards.reply_kb import generate_category_keyboard
from ..keyboards.inline_kb import financial_menu, category_menu, fin_confirmation_keyboard, edit_fin_options_keyboard, \
    expense_confirmation_keyboard, back_or_exit, main_menu
from ..models import Financial, Category, Expense
from ..utils.states import reset_financial_context, reset_all_context

(CHOOSE_EXPENSE_CATEGORY, SET_RESET_DAY, CATEGORY_NAME, CATEGORY_DESCRIPTION, CATEGORY_BUDGET_LIMIT,
 CONFIRM_CATEGORY_CREATION, CATEGORY_MENU, SELECT_EDIT_OPTION, SELECT_CATEGORY, CONFIRM_CATEGORY_EDIT
 , INPUT_EXPENSE_AMOUNT, INPUT_EXPENSE_DESCRIPTION, CONFIRM_EXPENSE_CREATION, BACK_OR_EXIT) = range(14)


async def get_finance_statistics(financial_info: Financial) -> str:
    total_limit = sum(category.budget_limit for category in financial_info.categories)
    total_expense = sum(expense.amount for category in financial_info.categories for expense in category.expenses)
    depleted_categories = [category for category in financial_info.categories if
                           sum(expense.amount for expense in category.expenses) >= category.budget_limit]
    day_of_reset = financial_info.reset_day

    statistics_message = (
        f"Потраченная сумма: {total_expense} / {total_limit}\n"
        f"Категорий с исчерпанным лимитом: {len(depleted_categories)}\n"
        f"День сброса: {day_of_reset}"
    )
    return statistics_message


async def get_statistics_by_categories(context: CallbackContext) -> str:
    financial_info = context.user_data.get('financial')
    statistics_message = "Статистика расходов:\n"
    warning_threshold = 0.9
    today = datetime.now(timezone.utc)
    reset_day = int(financial_info.reset_day)
    if today.day >= reset_day:
        start_date = today.replace(day=reset_day) - timedelta(days=30)
    else:
        previous_month = (today.replace(day=1) - timedelta(days=1)).month
        start_date = today.replace(day=reset_day, month=previous_month)
    for category in financial_info.categories:
        total_expense = 0
        for expense in category.expenses:
            expense_date = datetime.fromisoformat(expense.date)
            if expense_date >= start_date:
                total_expense += expense.amount

        warning_icon = ""
        if total_expense >= category.budget_limit:
            warning_icon = "🛑"
        elif total_expense >= category.budget_limit * warning_threshold:
            warning_icon = "⚠️"
        statistics_message += f"{category.name}: {total_expense}/{category.budget_limit} {warning_icon}\n"
    return statistics_message


async def create_new_financial(user_tid: int, context: CallbackContext):
    reset_day = datetime.now(timezone.utc).strftime('%d')
    financial = Financial(
        financial_oid='-',
        categories=list(),
        reset_day=reset_day,
        user_oid=context.user_data.get('user_data-db').user_oid
    )
    oid = await create_financial(financial)
    financial.financial_oid = oid
    return financial


async def finance_command(update: Update, context: CallbackContext) -> int:
    reset_all_context(context)
    context.user_data['user_data-db'] = await get_user(update.effective_user.id)
    financial_info = await get_financial_info(update.effective_user.id)
    if not financial_info:
        financial_info = await create_new_financial(update.effective_user.id, context)
    context.user_data['financial'] = financial_info
    user_id = update.effective_user.id
    stats_message = await get_finance_statistics(financial_info)

    await update.effective_user.send_message(f"{stats_message}", reply_markup=financial_menu())
    return ConversationHandler.END


async def send_categories_stats(update: Update, context: CallbackContext, orig_bot_msg: str):
    stats = await get_statistics_by_categories(context)
    await update.effective_user.send_message(stats, reply_markup=main_menu())
    return ConversationHandler.END


async def finance_menu_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    if query.data == 'finance_stats':
        return await send_categories_stats(update, context, query.message.text)
    elif query.data == 'finance_expense':
        financial_info = context.user_data['financial']
        categories = financial_info.categories
        context.user_data['add_expenses'] = True
        await query.message.reply_text("Выберите категорию для указания расходов",
                                       reply_markup=generate_category_keyboard(categories))
        return SELECT_CATEGORY
    elif query.data == 'finance_categories':
        await query.message.reply_text("Выберите действие:", reply_markup=category_menu())
        return CATEGORY_MENU
    elif query.data == 'finance_reset_day':
        await query.message.reply_text("Введите новый день сброса расходов (от 1 до 31). "
                                       "При указании дней 29-31 в месяцах с меньшим числом сброс произойдёт в"
                                       " последний день месяца",
                                       reply_markup=ReplyKeyboardRemove())
        return SET_RESET_DAY

    return ConversationHandler.END


async def set_reset_day(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    financial_info = context.user_data['financial']

    reset_day = update.message.text
    if not reset_day.isdigit() or int(reset_day) not in range(1, 32):
        await update.message.reply_text("Пожалуйста, введите корректный день (от 1 до 31).")
        return SET_RESET_DAY

    success = await update_reset_day(financial_info, int(reset_day))
    if success:
        await update.message.reply_text(f"День сброса успешно обновлен на {reset_day}.")
    else:
        await update.message.reply_text("Не удалось обновить день сброса. Попробуйте снова.")

    return ConversationHandler.END


async def category_menu_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    if query.data == 'create_category':
        await query.message.reply_text("Введите название новой категории:", reply_markup=ReplyKeyboardRemove())
        return CATEGORY_NAME
    elif query.data == 'edit_categories':
        financial_info = context.user_data['financial']
        categories = financial_info.categories
        await query.message.reply_text("Выберите категорию",
                                       reply_markup=generate_category_keyboard(categories))
        context.user_data['editing_category'] = True
        context.user_data['new_category'] = dict()
        return SELECT_CATEGORY

    return ConversationHandler.END


async def select_category(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    financial_info = context.user_data['financial']
    categories = financial_info.categories
    try:
        index = int(user_input.split(" - ")[0]) - 1
        selected_category = categories[index]
        context.user_data['selected_category'] = selected_category
        if context.user_data.get('add_expenses'):
            context.user_data.pop('add_expenses')
            await update.message.reply_text("Введите сумму расхода. Чтобы восполнить затраты, "
                                            "укажите отрицательную сумму например, -100",
                                            reply_markup=ReplyKeyboardRemove())
            return INPUT_EXPENSE_AMOUNT
        else:
            await update.message.reply_text("Что вы хотите изменить?", reply_markup=edit_fin_options_keyboard())
            return SELECT_EDIT_OPTION
    except (IndexError, ValueError):
        await update.message.reply_text("Неправильный ввод. Попробуйте снова.")
        return SELECT_CATEGORY


async def confirm_category_creation(update: Update, context: CallbackContext) -> int:
    if context.user_data.get('editing_category'):
        await confirm_category_edit(update, context)
        return CONFIRM_CATEGORY_EDIT
    confirmation_message = (
        "Подтвердите создание категории:\n"
        f"Название: {context.user_data['new_category']['name']}\n"
        f"Описание: {context.user_data['new_category']['description']}\n"
        f"Лимит: {context.user_data['new_category']['budget_limit']}")

    await update.message.reply_text(confirmation_message, reply_markup=fin_confirmation_keyboard())
    return CONFIRM_CATEGORY_CREATION


async def create_category_name(update: Update, context: CallbackContext) -> int:
    category_name = update.message.text
    if context.user_data.get('editing_new_category'):
        context.user_data['new_category']['name'] = category_name
        context.user_data['editing_new_category'] = False
        retval = await confirm_category_creation(update, context)
        return retval
    context.user_data['new_category'] = {'name': category_name}
    await update.message.reply_text("Введите описание категории:")
    return CATEGORY_DESCRIPTION


async def create_category_description(update: Update, context: CallbackContext) -> int:
    category_description = update.message.text
    context.user_data['new_category']['description'] = category_description
    if context.user_data.get('editing_new_category'):
        context.user_data['editing_new_category'] = False
        retval = await confirm_category_creation(update, context)
        return retval
    await update.message.reply_text("Введите бюджетный лимит категории:")
    return CATEGORY_BUDGET_LIMIT


async def create_category_budget_limit(update: Update, context: CallbackContext) -> int:
    budget_limit = update.message.text
    if not budget_limit.replace('.', '', 1).isdigit():
        await update.message.reply_text("Пожалуйста, введите корректное число.")
        return CATEGORY_BUDGET_LIMIT

    context.user_data['new_category']['budget_limit'] = float(budget_limit)
    return await confirm_category_creation(update, context)


async def handle_category_confirm(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'fin_confirm_yes':
        financial_info = context.user_data['financial']
        new_category_data = {
            'category_id': '-',
            'name': context.user_data['new_category']['name'],
            'description': context.user_data['new_category']['description'],
            'budget_limit': context.user_data['new_category']['budget_limit'],
            'expenses': []
        }
        new_category = Category(**new_category_data)
        financial_info.categories.append(new_category)
        success = await create_category(financial_info, new_category)
        if success:
            await query.message.reply_text("Категория создана.", reply_markup=ReplyKeyboardRemove())
        else:
            await query.message.reply_text("Не удалось создать категорию. Попробуйте снова.",
                                           reply_markup=ReplyKeyboardRemove())
        reset_financial_context(context)
        return ConversationHandler.END
    elif query.data == 'fin_confirm_edit':
        await query.message.delete()
        await query.message.reply_text("Что вы хотите изменить?", reply_markup=edit_fin_options_keyboard())
        return SELECT_EDIT_OPTION


async def handle_edit_fin_option(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    if query.data == 'fin_edit_title':
        await update.effective_user.send_message("Введите новое название категории:")
        context.user_data['editing_new_category'] = True
        return CATEGORY_NAME
    elif query.data == 'fin_edit_description':
        await update.effective_user.send_message("Введите новое описание категории:")
        context.user_data['editing_new_category'] = True
        return CATEGORY_DESCRIPTION
    elif query.data == 'fin_edit_limit':
        await update.effective_user.send_message("Введите новый бюджетный лимит категории:")
        context.user_data['editing_new_category'] = True
        return CATEGORY_BUDGET_LIMIT


"""EDITING categories"""


async def confirm_category_edit(update: Update, context: CallbackContext):
    old_category = context.user_data.get('selected_category')
    category = Category(category_id='-', name=old_category.name,  budget_limit=old_category.budget_limit,
                        expenses=old_category.expenses, description=old_category.description)
    new_category = context.user_data.get('new_category')
    category.name = new_category.get('name', category.name)
    category.description = new_category.get('description',  category.description)
    category.budget_limit = new_category.get('budget_limit',  category.budget_limit)
    context.user_data['edited_category'] = category
    confirmation_message = (
        "Подтвердите изменение категории:\n"
        f"Название: {category.name}\n"
        f"Описание: {category.description}\n"
        f"Лимит: {category.budget_limit}")
    await update.message.reply_text(confirmation_message, reply_markup=fin_confirmation_keyboard())


async def handle_category_edit_confirm(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    if query.data == 'fin_confirm_yes':
        financial_info = context.user_data['financial']
        old_category = context.user_data.get('selected_category')
        new_category = context.user_data.get('edited_category')
        success = await update_category(financial_info, old_category.name,
                                        old_category.description, new_category)
        if success:
            await query.message.reply_text("Категория обновлена", reply_markup=ReplyKeyboardRemove())
        else:
            await query.message.reply_text("Не удалось обновить категорию. Попробуйте снова.",
                                           reply_markup=ReplyKeyboardRemove())
        reset_financial_context(context)
        return ConversationHandler.END
    elif query.data == 'fin_confirm_edit':
        await query.message.reply_text("Что вы хотите изменить?", reply_markup=edit_fin_options_keyboard())
        return SELECT_EDIT_OPTION

"""EXPENSE_INPUT"""


async def input_expense_amount(update: Update, context: CallbackContext) -> int:
    amount = update.message.text
    if not re.match(r'^-?\d+(\.\d+)?$', amount):
        await update.message.reply_text("Пожалуйста, введите корректное число.")
        return INPUT_EXPENSE_AMOUNT

    context.user_data['new_expense'] = {'amount': float(amount)}
    await update.message.reply_text("Введите описание расхода:")
    return INPUT_EXPENSE_DESCRIPTION


async def input_expense_description(update: Update, context: CallbackContext) -> int:
    description = update.message.text
    context.user_data['new_expense']['description'] = description
    selected_category = context.user_data['selected_category']
    await update.message.reply_text(f"Подтвердите добавление расхода:\n"
                                    f"Категория: {selected_category.name}\n"
                                    f"Сумма: {context.user_data['new_expense']['amount']}\n"
                                    f"Описание: {description}",
                                    reply_markup=expense_confirmation_keyboard())
    return CONFIRM_EXPENSE_CREATION


async def handle_expense_confirm(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    category = context.user_data.get('selected_category')
    expense = context.user_data.get('new_expense')
    if query.data == 'expense_confirm_yes':
        user = await get_user(update.effective_user.id)
        new_expense = Expense(expense_id='-',
                              amount=expense.get('amount', .0),
                              description=expense.get('description', ""),
                              date=datetime.now(timezone.utc).isoformat(),
                              user_oid=user.user_oid)
        if await create_expense(context.user_data.get('financial').financial_oid, category, new_expense):
            await query.message.reply_text("Расход добавлен.", reply_markup=ReplyKeyboardRemove())
        else:
            await query.message.reply_text("Не удалось добавить расход. Попробуйте снова.",
                                           reply_markup=ReplyKeyboardRemove())
        reset_financial_context(context)
        return ConversationHandler.END
    elif query.data == 'expense_confirm_edit':
        await query.message.reply_text(f"Повторный ввод расхода для категории {category.name}.\n"
                                       f"Было: {expense.get('description')} - на сумму {expense.get('amount')}\n\n"
                                       f"Введите новую сумму:")
        return INPUT_EXPENSE_AMOUNT


async def back_or_exit_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    await query.message.delete()
    if action == 'back':
        message = context.user_data.get('back_message', {"text": "Возвращаю назад"})
        previous_state = context.user_data.get('previous_state', ConversationHandler.END)
        await update.effective_user.send_message(text=message.get('text'), reply_markup=message.get('reply_markup'))
        return previous_state
    elif action == 'exit':
        context.user_data.clear()
        await query.message.reply_text("Вы завершили взаимодействие и вернулись в главное меню.", reply_markup=main_menu())
        return ConversationHandler.END


financial_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(finance_menu_callback, pattern=r'^finance_')],
    states={
        SET_RESET_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_reset_day)],
        CATEGORY_MENU: [CallbackQueryHandler(category_menu_callback, pattern=r'^(create_category|edit_categories)$')],
        CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_category_name)],
        CATEGORY_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_category_description)],
        CATEGORY_BUDGET_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_category_budget_limit)],
        CONFIRM_CATEGORY_CREATION: [CallbackQueryHandler(handle_category_confirm, pattern=r'^fin_confirm')],
        SELECT_EDIT_OPTION: [CallbackQueryHandler(handle_edit_fin_option, pattern=r'^fin_edit_')],
        CONFIRM_CATEGORY_EDIT: [CallbackQueryHandler(handle_category_edit_confirm, pattern=r'^fin_confirm')],
        SELECT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_category)],
        INPUT_EXPENSE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_expense_description)],
        INPUT_EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_expense_amount)],
        CONFIRM_EXPENSE_CREATION: [CallbackQueryHandler(handle_expense_confirm, pattern=r'^expense_confirm')],
        BACK_OR_EXIT: [CallbackQueryHandler(back_or_exit_handler, pattern=r'^(back|exit)$')]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
