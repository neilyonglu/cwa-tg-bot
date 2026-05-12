from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from handlers._utils import build_fav_keyboard, send_place_radar
from models import favorite as fav_model


async def fav_command(update, context):
    user_id = update.effective_user.id
    favorites = await fav_model.get_favorites(user_id)
    if not favorites:
        await update.message.reply_text(
            "⭐ 你還沒有儲存任何喜愛點。\n\n使用 `/place` 查詢地點後，可以按「⭐ 加入喜愛點」儲存。",
            parse_mode="Markdown",
        )
        return
    await update.message.reply_text(
        f"⭐ *我的喜愛點*（{len(favorites)}/{fav_model.MAX_FAVORITES}）\n\n點選地點查詢即時雨勢，或按 🗑️ 刪除。",
        parse_mode="Markdown",
        reply_markup=build_fav_keyboard(favorites),
    )


async def handle_text(update, context) -> bool:
    if not context.user_data.get("awaiting_fav_name"):
        return False
    fav_name = update.message.text.strip()
    last = context.user_data.get("last_place")
    context.user_data["awaiting_fav_name"] = False
    if not fav_name or not last:
        await update.message.reply_text("❌ 命名失敗，請重新查詢地點後再加入。")
        return True
    user_id = update.effective_user.id
    result = await fav_model.add_favorite(user_id, fav_name, last["lat"], last["lon"])
    if "error" in result:
        if result["error"] == "limit_exceeded":
            await update.message.reply_text(
                f"❌ 最多只能儲存 {fav_model.MAX_FAVORITES} 個喜愛點，請先刪除舊的（/fav）。"
            )
        else:
            await update.message.reply_text(f"「{fav_name}」已在喜愛點中。")
    else:
        await update.message.reply_text(f"⭐ 已將「{fav_name}」加入喜愛點！")
    return True


async def _handle_action_fav(update, context):
    await update.callback_query.answer()
    user_id = update.callback_query.from_user.id
    favorites = await fav_model.get_favorites(user_id)
    if not favorites:
        await update.callback_query.message.reply_text(
            "⭐ 你還沒有儲存任何喜愛點。\n\n使用 `/place` 查詢地點後，可以按「⭐ 加入喜愛點」儲存。",
            parse_mode="Markdown",
        )
    else:
        await update.callback_query.message.reply_text(
            f"⭐ *我的喜愛點*（{len(favorites)}/{fav_model.MAX_FAVORITES}）\n\n點選地點查詢即時雨勢，或按 🗑️ 刪除。",
            parse_mode="Markdown",
            reply_markup=build_fav_keyboard(favorites),
        )


async def _handle_fav_add(update, context):
    query = update.callback_query
    await query.answer()
    last = context.user_data.get("last_place")
    if not last:
        await query.message.reply_text("❌ 找不到最近查詢的地點，請先使用 /place 查詢。")
        return
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    context.user_data["awaiting_fav_name"] = True
    await query.message.reply_text(f"📍 {last['name']}\n\n請為這個地點取個名稱（例如：公司、家、學校）：")


async def _handle_fav_query(update, context):
    query = update.callback_query
    await query.answer()
    fav_id = int(query.data.split("_")[2])
    favorites = await fav_model.get_favorites(query.from_user.id)
    fav = next((f for f in favorites if f["id"] == fav_id), None)
    if fav:
        await send_place_radar(query.message, context, fav["lat"], fav["lon"], fav["name"], show_add_fav=False)
    else:
        await query.message.reply_text("❌ 找不到此喜愛點，可能已被刪除。")


async def _handle_fav_delete(update, context):
    query = update.callback_query
    fav_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    await fav_model.delete_favorite(fav_id, user_id)
    favorites = await fav_model.get_favorites(user_id)
    try:
        if not favorites:
            await query.edit_message_text("⭐ 喜愛點已全部清空。")
        else:
            await query.edit_message_text(
                f"⭐ *我的喜愛點*（{len(favorites)}/{fav_model.MAX_FAVORITES}）\n\n點選地點查詢即時雨勢，或按 🗑️ 刪除。",
                parse_mode="Markdown",
                reply_markup=build_fav_keyboard(favorites),
            )
    except Exception:
        await query.message.reply_text("🗑️ 已刪除。")
    await query.answer("已刪除 ✓")


def register(app):
    app.add_handler(CommandHandler("fav", fav_command))
    app.add_handler(CallbackQueryHandler(_handle_action_fav, pattern="^action_fav$"))
    app.add_handler(CallbackQueryHandler(_handle_fav_add, pattern="^fav_add$"))
    app.add_handler(CallbackQueryHandler(_handle_fav_query, pattern=r"^fav_q_\d+$"))
    app.add_handler(CallbackQueryHandler(_handle_fav_delete, pattern=r"^fav_d_\d+$"))
