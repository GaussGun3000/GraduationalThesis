from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, CommandHandler, filters, \
    CallbackQueryHandler

from .basic_commands import cancel
from ..utils.api import get_user_tasks, update_task, create_task, get_user, delete_task, get_financial_info, \
    create_financial, update_reset_day, create_category, update_category, create_expense, get_group, create_group
from datetime import datetime, timezone, timedelta
from dateutil.parser import isoparse
from ..keyboards.reply_kb import active_tasks_keyboard, recurring_keyboard, generate_category_keyboard
from ..keyboards.inline_kb import financial_menu, category_menu, fin_confirmation_keyboard, edit_fin_options_keyboard, \
    expense_confirmation_keyboard, select_group_keyboard
from ..models import Group, GroupMember
from ..utils.states import reset_financial_context

() = range(13)

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler
from ..utils.api import get_created_group, get_user_groups


async def group_command(update: Update, context: CallbackContext) -> None:
    user_tid = update.effective_user.id
    created_group = await get_created_group(user_tid)
    user_groups = await get_user_groups(user_tid)
    user_data = await get_user(user_tid)
    context.user_data['user_data-db'] = user_data
    if created_group:
        context.user_data['my_group'] = created_group
    if not created_group and not user_groups and not user_data.is_premium():
        await update.message.reply_text("Вы не состоите в группах и у вас нет премиума для создания группы.")
        return

    await update.message.reply_text("Выберите группу для управления:",
                                    reply_markup=select_group_keyboard(user_data, created_group, user_groups))


CREATE_GROUP_NAME, = range(1)


async def group_selection_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    user_tid = update.effective_user.id
    user_data = context.user_data['user_data-db']

    if query.data == 'group_my ':
        created_group = context.user_data.get('my_group')
        if not created_group:
            await query.message.reply_text("Введите название для новой группы:", reply_markup=ReplyKeyboardRemove())
            return CREATE_GROUP_NAME
        else:
            created_group = await get_group(created_group)
            await query.message.reply_text(f"Группа: {created_group['name']}")
            # Здесь вы можете добавить логику для работы с существующей группой.
            return ConversationHandler.END

    # Обработка других групп
    if query.data.startswith('group_'):
        group_id = query.data.split('_')[1]
        await query.message.reply_text(f"Вы выбрали группу с ID: {group_id}")
        # Добавьте логику для работы с выбранной группой.
        return ConversationHandler.END


async def create_group_name(update: Update, context: CallbackContext) -> int:
    group_name = update.message.text
    user_tid = update.effective_user.id
    user_data = context.user_data['user_data-db']

    new_group = await create_group(user_tid, group_name)
    if new_group:
        await update.message.reply_text(f"Группа '{group_name}' создана.")
        context.user_data['groups'].append(new_group)
    else:
        await update.message.reply_text("Не удалось создать группу. Попробуйте снова.")

    return ConversationHandler.END


group_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(group_selection_callback, pattern=r'^group_')],
    states={
        CREATE_GROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_group_name)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)