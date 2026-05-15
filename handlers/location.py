from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
from handlers._utils import radar_service
from services import llm_service
from models import user as user_model


async def request_location(update, context):
    location_button = KeyboardButton(text="📍 發送目前位置", request_location=True)
    await update.message.reply_text(
        "請點擊下方按鈕，查詢當地的降雨資訊 🌤️",
        reply_markup=ReplyKeyboardMarkup(
            [[location_button]], resize_keyboard=True, one_time_keyboard=True
        ),
    )


async def handle_location(update, context):
    user = update.effective_user
    await user_model.save_user(user.id, user.username or "")
    user_location = update.message.location
    lat, lon = user_location.latitude, user_location.longitude

    processing_msg = await update.message.reply_text(
        "⏳ 正在產生雷達降雨圖，請稍候...",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        img_bytes, img_time_str, rain_desc = await radar_service.get_marked_radar(
            lat, lon
        )
        if img_bytes:
            rain_desc = rain_desc or "☀️ 目前無明顯降雨"
            llm_desc = await llm_service.analyze_rainfall(
                "目前位置", img_time_str, rain_desc
            )
            context.user_data["last_place"] = {
                "name": "目前位置",
                "lat": lat,
                "lon": lon,
            }
            await update.message.reply_photo(
                photo=img_bytes,
                caption=f"📍 目前位置\n🕒 時間：{img_time_str}\n{llm_desc or rain_desc}",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⭐ 加入喜愛點", callback_data="fav_add")]]
                ),
            )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text(
                "❌ 抱歉，目前無法取得氣象雷達圖資，請稍後再試。"
            )
    except Exception as e:
        print(f"處理雷達圖發生錯誤: {e}")
        await processing_msg.edit_text("❌ 發生系統錯誤，請稍後再試。")


async def _handle_action_nearby(update, context):
    await update.callback_query.answer()
    location_button = KeyboardButton(text="📍 發送目前位置", request_location=True)
    await update.callback_query.message.reply_text(
        "請點擊下方按鈕，查詢當地的降雨資訊 🌤️",
        reply_markup=ReplyKeyboardMarkup(
            [[location_button]], resize_keyboard=True, one_time_keyboard=True
        ),
    )


def register(app):
    app.add_handler(CommandHandler("nearby", request_location))
    app.add_handler(
        CallbackQueryHandler(_handle_action_nearby, pattern="^action_nearby$")
    )
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
