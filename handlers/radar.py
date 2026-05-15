from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, CallbackQueryHandler
from handlers._utils import radar_service

REGION_MAP = {"北部": "north", "中部": "central", "南部": "south"}


async def radar_menu(update, context):
    keyboard = [
        [KeyboardButton("北部"), KeyboardButton("中部")],
        [KeyboardButton("南部")],
    ]
    await update.message.reply_text(
        "請選擇要查詢的區域：",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        ),
    )


async def handle_text(update, context) -> bool:
    text = update.message.text
    if text not in REGION_MAP:
        return False
    region_key = REGION_MAP[text]
    processing_msg = await update.message.reply_text(
        f"⏳ 正在抓取{text}，請稍候...", reply_markup=ReplyKeyboardRemove()
    )
    try:
        img_bytes, img_time_str = await radar_service.get_region_radar(region_key)
        if img_bytes:
            await update.message.reply_photo(
                photo=img_bytes,
                caption=f"📡 {text}\n🕒 時間：{img_time_str}",
            )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ 無法取得該區域雷達圖，請稍後再試。")
    except Exception as e:
        print(f"處理區域雷達發生錯誤: {e}")
        await processing_msg.edit_text("❌ 發生系統錯誤，請稍後再試。")
    return True


async def _handle_action_radar(update, context):
    await update.callback_query.answer()
    keyboard = [
        [KeyboardButton("北部"), KeyboardButton("中部")],
        [KeyboardButton("南部")],
    ]
    await update.callback_query.message.reply_text(
        "請選擇要查詢的區域：",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        ),
    )


def register(app):
    app.add_handler(CommandHandler("radar", radar_menu))
    app.add_handler(
        CallbackQueryHandler(_handle_action_radar, pattern="^action_radar$")
    )
