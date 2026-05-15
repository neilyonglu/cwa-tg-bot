import os
import requests
from telegram import ReplyKeyboardRemove
from telegram.ext import CommandHandler, CallbackQueryHandler
from handlers._utils import send_place_radar

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def resolve_place_to_latlon(place_name: str):
    query = (place_name or "").strip()
    if not query:
        return None, None, "", "not_found"

    api_key = os.environ.get("GOOGLE_MAPS_KEY")
    if not api_key:
        print("⚠️ 警告：未設定 GOOGLE_MAPS_KEY，跳過 Google 查詢。")
    else:
        try:
            response = requests.get(
                GOOGLE_GEOCODE_URL,
                params={
                    "address": query,
                    "key": api_key,
                    "language": "zh-TW",
                    "region": "tw",
                },
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                lat = float(result["geometry"]["location"]["lat"])
                lon = float(result["geometry"]["location"]["lng"])
                return lat, lon, result.get("formatted_address", query), "google"
            elif data.get("status") != "ZERO_RESULTS":
                print(f"[Google API 錯誤] Status: {data.get('status')}")
        except Exception as exc:
            print(f"[Google Geocoding 失敗] {exc}")

    return None, None, query, "not_found"


async def request_place(update, context):
    context.user_data["awaiting_place_input"] = True
    await update.message.reply_text(
        "請輸入要查詢的地點或地址。",
        reply_markup=ReplyKeyboardRemove(),
    )


async def handle_text(update, context) -> bool:
    if not context.user_data.get("awaiting_place_input"):
        return False
    text = update.message.text
    lat, lon, _, _ = resolve_place_to_latlon(text)
    if lat is None:
        await update.message.reply_text(
            f"❌ 找不到「{text}」這個地點，請重新輸入更完整的地名（例如：台北101）。"
        )
        return True
    context.user_data["awaiting_place_input"] = False
    await send_place_radar(update.message, context, lat, lon, text)
    return True


async def _handle_action_place(update, context):
    await update.callback_query.answer()
    context.user_data["awaiting_place_input"] = True
    await update.callback_query.message.reply_text(
        "請輸入要查詢的地點名稱（例如：台北101）。",
        reply_markup=ReplyKeyboardRemove(),
    )


def register(app):
    app.add_handler(CommandHandler("place", request_place))
    app.add_handler(
        CallbackQueryHandler(_handle_action_place, pattern="^action_place$")
    )
