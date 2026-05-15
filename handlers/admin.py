import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, CallbackQueryHandler
from handlers._utils import build_inbox_text_and_keyboard
from models import feedback as feedback_model

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "6501701404")


async def feedback_command(update, context):
    context.user_data["awaiting_feedback"] = True
    await update.message.reply_text(
        "💬 請輸入你的回饋或建議，我們會認真閱讀：",
        reply_markup=ReplyKeyboardRemove(),
    )


async def inbox_command(update, context):
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
        return
    feedbacks = await feedback_model.get_all_feedback()
    if not feedbacks:
        await update.message.reply_text("📭 目前沒有任何回饋。")
        return
    context.user_data["inbox_feedback_ids"] = [fb["id"] for fb in feedbacks]
    text, keyboard = build_inbox_text_and_keyboard(feedbacks)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_text(update, context) -> bool:
    text = update.message.text

    if context.user_data.get("awaiting_feedback_delete"):
        if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
            return False
        ids = context.user_data.get("inbox_feedback_ids", [])
        try:
            num = int(text.strip())
            if not (1 <= num <= len(ids)):
                await update.message.reply_text(f"❌ 請輸入 1 到 {len(ids)} 之間的數字。")
                return True
            context.user_data["awaiting_feedback_delete"] = False
            await feedback_model.delete_feedback_item(ids[num - 1])
            feedbacks = await feedback_model.get_all_feedback()
            context.user_data["inbox_feedback_ids"] = [fb["id"] for fb in feedbacks]
            if not feedbacks:
                await update.message.reply_text("📭 所有回饋已清空。")
            else:
                msg, keyboard = build_inbox_text_and_keyboard(feedbacks)
                await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)
        except ValueError:
            await update.message.reply_text("❌ 請輸入數字。")
        return True

    if context.user_data.get("awaiting_feedback"):
        feedback_text = text.strip()
        context.user_data["awaiting_feedback"] = False
        if not feedback_text:
            await update.message.reply_text("回饋不能為空，請重新使用 /feedback 提交。")
            return True
        user = update.effective_user
        await feedback_model.add_feedback(user.id, user.username or "", feedback_text)
        await update.message.reply_text("✅ 感謝你的回饋！我們會認真參考。")
        return True

    return False


async def _handle_inbox_delete(update, context):
    query = update.callback_query
    if str(query.from_user.id) != str(ADMIN_CHAT_ID):
        await query.answer()
        return
    ids = context.user_data.get("inbox_feedback_ids", [])
    if not ids:
        await query.answer("沒有可刪除的項目")
        return
    await query.answer()
    context.user_data["awaiting_feedback_delete"] = True
    await query.message.reply_text(f"請輸入要刪除的編號（1－{len(ids)}）：")


def register(app):
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("inbox", inbox_command))
    app.add_handler(CallbackQueryHandler(_handle_inbox_delete, pattern="^inbox_delete$"))
