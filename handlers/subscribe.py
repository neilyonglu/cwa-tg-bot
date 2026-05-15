from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler
from models import user as user_model


async def subscribe_command(update, context):
    user = update.effective_user
    await user_model.save_user(user.id, user.username or "")
    is_subscribed = await user_model.get_subscription_status(user.id)
    await _send_subscribe_status(update.message, is_subscribed)


async def _send_subscribe_status(message, is_subscribed: bool):
    if is_subscribed:
        text = "🔔 *你目前已訂閱更新通知*\n\n伺服器有新功能時，你會收到通知。"
        button_label = "🔕 取消訂閱"
    else:
        text = "🔕 *你目前未訂閱更新通知*\n\n訂閱後，伺服器有新功能時會主動通知你。"
        button_label = "🔔 訂閱更新通知"
    await message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(button_label, callback_data="sub_toggle")]]
        ),
    )


async def _handle_sub_toggle(update, context):
    query = update.callback_query
    await query.answer()
    new_state = await user_model.toggle_subscription(query.from_user.id)
    await query.edit_message_text(
        "🔔 *已開啟更新通知！*\n\n伺服器有新功能時，你會收到通知。"
        if new_state
        else "🔕 *已取消訂閱。*\n\n你不會再收到更新通知。",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔕 取消訂閱" if new_state else "🔔 重新訂閱",
                        callback_data="sub_toggle",
                    )
                ]
            ]
        ),
    )


def register(app):
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CallbackQueryHandler(_handle_sub_toggle, pattern="^sub_toggle$"))
