from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from services.radar_service import RadarService
from services import llm_service

radar_service = RadarService()


def build_fav_keyboard(favorites: list) -> InlineKeyboardMarkup:
    keyboard = []
    for fav in favorites:
        keyboard.append([
            InlineKeyboardButton(f"📍 {fav['name']}", callback_data=f"fav_q_{fav['id']}"),
            InlineKeyboardButton("🗑️", callback_data=f"fav_d_{fav['id']}"),
        ])
    return InlineKeyboardMarkup(keyboard)


def build_inbox_text_and_keyboard(feedbacks: list):
    lines = [f"📬 *回饋列表*（共 {len(feedbacks)} 筆）\n"]
    for i, fb in enumerate(feedbacks, 1):
        username = f"@{fb['username']}" if fb["username"] else f"ID:{fb['user_id']}"
        dt = fb["created_at"].strftime("%m-%d %H:%M") if fb["created_at"] else ""
        lines.append(f"*{i}.* {username} | {dt}\n{fb['text']}\n")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n...(已截斷)"
    keyboard = [[InlineKeyboardButton("🗑️ 刪除", callback_data="inbox_delete")]]
    return text, InlineKeyboardMarkup(keyboard)


async def send_place_radar(
    message, context: ContextTypes.DEFAULT_TYPE,
    lat: float, lon: float, place_label: str,
    show_add_fav: bool = True,
):
    processing_msg = await message.reply_text(
        f"⏳ 正在查詢「{place_label}」的降雨資訊，請稍候...",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        img_bytes, img_time_str, rain_desc = await radar_service.get_marked_radar(lat, lon)
        if img_bytes:
            rain_desc = rain_desc or "☀️ 目前無明顯降雨"
            llm_desc = await llm_service.analyze_rainfall(place_label, img_time_str, rain_desc)
            reply_markup = None
            if show_add_fav:
                context.user_data["last_place"] = {"name": place_label, "lat": lat, "lon": lon}
                reply_markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⭐ 加入喜愛點", callback_data="fav_add")]]
                )
            await message.reply_photo(
                photo=img_bytes,
                caption=f"📍 地點：{place_label}\n🕒 時間：{img_time_str}\n{llm_desc or rain_desc}",
                reply_markup=reply_markup,
            )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ 抱歉，目前無法取得該地點的雷達圖資，請稍後再試。")
    except Exception as e:
        print(f"處理地點雷達發生錯誤: {e}")
        await processing_msg.edit_text("❌ 發生系統錯誤，請稍後再試。")
