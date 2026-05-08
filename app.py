import os
import asyncio
import threading
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes,
)
from services.radar_service import RadarService
from services import db_service

# ── 常數 ────────────────────────────────────────────────────────────

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "6501701404")
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_MAPS_API_KEY = os.environ.get("GEMINI_API_KEY")

BOT_COMMANDS = [
    BotCommand("start", "🌦 開始使用"),
    BotCommand("fav", "⭐ 我的喜愛點"),
    BotCommand("nearby", "📍 查詢現在位置雨量"),
    BotCommand("place", "🔎 輸入地點查雨勢"),
    BotCommand("radar", "📡 查詢區域雷達圖"),
    BotCommand("feedback", "💬 提供回饋"),
    BotCommand("manual", "📖 使用說明書"),
]

radar_service = RadarService()


# ── 輔助函式 ─────────────────────────────────────────────────────────

def resolve_place_to_latlon(place_name: str):
    query = (place_name or "").strip()
    if not query:
        return None, None, "", "not_found"

    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ 警告：未設定 GEMINI_API_KEY，跳過 Google 查詢。")
    else:
        try:
            response = requests.get(
                GOOGLE_GEOCODE_URL,
                params={
                    "address": query,
                    "key": GOOGLE_MAPS_API_KEY,
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
                display_name = result.get("formatted_address", query)
                return lat, lon, display_name, "google"
            elif data.get("status") != "ZERO_RESULTS":
                print(f"[Google API 錯誤] Status: {data.get('status')}")
        except Exception as exc:
            print(f"[Google Geocoding 失敗] {exc}")

    return None, None, query, "not_found"


def _build_fav_keyboard(favorites: list) -> InlineKeyboardMarkup:
    keyboard = []
    for fav in favorites:
        keyboard.append([
            InlineKeyboardButton(f"📍 {fav['name']}", callback_data=f"fav_q_{fav['id']}"),
            InlineKeyboardButton("🗑️", callback_data=f"fav_d_{fav['id']}"),
        ])
    return InlineKeyboardMarkup(keyboard)


def _build_inbox_text_and_keyboard(feedbacks: list):
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


async def _send_place_radar(
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
            reply_markup = None
            if show_add_fav:
                context.user_data["last_place"] = {"name": place_label, "lat": lat, "lon": lon}
                reply_markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⭐ 加入喜愛點", callback_data="fav_add")]]
                )
            await message.reply_photo(
                photo=img_bytes,
                caption=f"📍 地點：{place_label}\n🕒 時間：{img_time_str}\n{rain_desc}",
                reply_markup=reply_markup,
            )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ 抱歉，目前無法取得該地點的雷達圖資，請稍後再試。")
    except Exception as e:
        print(f"處理地點雷達發生錯誤: {e}")
        await processing_msg.edit_text("❌ 發生系統錯誤，請稍後再試。")


# ── 指令處理 ─────────────────────────────────────────────────────────

async def post_init(application: Application):
    await application.bot.set_my_commands(BOT_COMMANDS)
    print("--- 左下角快捷選單已自動同步 ---")
    try:
        await application.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="🚀 **系統更新完成！**\n\n",
            parse_mode="Markdown",
        )
        print(f"--- 已發送系統更新通知給 {ADMIN_CHAT_ID} ---")
    except Exception as e:
        print(f"--- 無法發送更新通知給管理員: {e} ---")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📍 查詢現在位置", callback_data="action_nearby"),
            InlineKeyboardButton("🔎 查詢指定地點", callback_data="action_place"),
        ],
        [
            InlineKeyboardButton("📡 區域雷達圖", callback_data="action_radar"),
            InlineKeyboardButton("⭐ 我的喜愛點", callback_data="action_fav"),
        ],
    ]
    msg = (
        "🌦 *氣象雷達機器人*\n\n"
        "即時查詢台灣各地降雨資訊，資料來源：中央氣象署 (CWA)。\n\n"
        "📍 `/nearby` — 查詢現在位置\n"
        "🔎 `/place` — 輸入地點查雨勢\n"
        "📡 `/radar` — 大區域雷達圖\n"
        "⭐ `/fav` — 我的喜愛點\n"
        "📖 `/manual` — 使用說明書"
    )
    await update.message.reply_text(
        msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location_button = KeyboardButton(text="📍 發送目前位置", request_location=True)
    await update.message.reply_text(
        "請點擊下方按鈕，查詢當地的降雨資訊 🌤️",
        reply_markup=ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True),
    )


async def radar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("北部"), KeyboardButton("中部")],
        [KeyboardButton("南部")],
    ]
    await update.message.reply_text(
        "請選擇要查詢的區域：",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
    )


async def fav_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    favorites = await db_service.get_favorites(user_id)
    if not favorites:
        await update.message.reply_text(
            "⭐ 你還沒有儲存任何喜愛點。\n\n使用 `/place` 查詢地點後，可以按「⭐ 加入喜愛點」儲存。",
            parse_mode="Markdown",
        )
        return
    await update.message.reply_text(
        f"⭐ *我的喜愛點*（{len(favorites)}/{db_service.MAX_FAVORITES}）\n\n點選地點查詢即時雨勢，或按 🗑️ 刪除。",
        parse_mode="Markdown",
        reply_markup=_build_fav_keyboard(favorites),
    )


async def request_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_place_input"] = True
    await update.message.reply_text(
        "請輸入要查詢的地點或地址。",
        reply_markup=ReplyKeyboardRemove(),
    )


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_feedback"] = True
    await update.message.reply_text(
        "💬 請輸入你的回饋或建議，我們會認真閱讀：",
        reply_markup=ReplyKeyboardRemove(),
    )


async def inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
        return
    feedbacks = await db_service.get_all_feedback()
    if not feedbacks:
        await update.message.reply_text("📭 目前沒有任何回饋。")
        return
    context.user_data["inbox_feedback_ids"] = [fb["id"] for fb in feedbacks]
    text, keyboard = _build_inbox_text_and_keyboard(feedbacks)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 **氣象雷達機器人 使用說明書**\n\n"
        "本機器人串接中央氣象署 (CWA) 即時圖資，提供精準的降雨趨勢查詢。\n\n"
        "📍 **功能介紹：**\n"
        "1. `/nearby` - **查詢目前位置**\n"
        "   發送你的 GPS 座標，機器人會回傳以你為中心的雷達圖，並自動分析降雨強度。\n\n"
        "2. `/place` - **查詢指定地點**\n"
        "   輸入地名或地址（例如：`台北101`），系統會精準定位並顯示當地即時雨勢。\n\n"
        "3. `/radar` - **大區域雷達圖**\n"
        "   快速切換查看「北部、中部、南部」的大範圍降雨分佈。\n\n"
        "4. `/fav` - **我的喜愛點**\n"
        "   儲存常用地點（最多 5 個），一鍵查詢即時雨勢。\n\n"
        "🖼️ **結果解讀：**\n"
        "• **紅色圓點**：代表你查詢的確切目標位置。\n"
        "• **彩色區塊**：代表降雨強度（綠色 < 藍色 < 黃色 < 紅色 < 紫色）。\n"
        "• **分析文字**：機器人會自動告訴你目前是「無明顯降雨」或有降雨風險。\n\n"
        "⚠️ **小提醒：**\n"
        "• 氣象署圖資約每 2-10 分鐘更新一次。\n"
        "• 若地點搜尋不到，請嘗試輸入更完整的行政區名稱。"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ── 事件處理 ─────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "action_nearby":
        await query.answer()
        location_button = KeyboardButton(text="📍 發送目前位置", request_location=True)
        await query.message.reply_text(
            "請點擊下方按鈕，查詢當地的降雨資訊 🌤️",
            reply_markup=ReplyKeyboardMarkup(
                [[location_button]], resize_keyboard=True, one_time_keyboard=True
            ),
        )

    elif data == "action_place":
        await query.answer()
        context.user_data["awaiting_place_input"] = True
        await query.message.reply_text(
            "請輸入要查詢的地點名稱（例如：台北101）。",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif data == "action_radar":
        await query.answer()
        keyboard = [
            [KeyboardButton("北部"), KeyboardButton("中部")],
            [KeyboardButton("南部")],
        ]
        await query.message.reply_text(
            "請選擇要查詢的區域：",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        )

    elif data == "action_fav":
        await query.answer()
        user_id = query.from_user.id
        favorites = await db_service.get_favorites(user_id)
        if not favorites:
            await query.message.reply_text(
                "⭐ 你還沒有儲存任何喜愛點。\n\n使用 `/place` 查詢地點後，可以按「⭐ 加入喜愛點」儲存。",
                parse_mode="Markdown",
            )
        else:
            await query.message.reply_text(
                f"⭐ *我的喜愛點*（{len(favorites)}/{db_service.MAX_FAVORITES}）\n\n點選地點查詢即時雨勢，或按 🗑️ 刪除。",
                parse_mode="Markdown",
                reply_markup=_build_fav_keyboard(favorites),
            )

    elif data == "fav_add":
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
        await query.message.reply_text(
            f"📍 {last['name']}\n\n請為這個地點取個名稱（例如：公司、家、學校）："
        )

    elif data.startswith("fav_q_"):
        await query.answer()
        fav_id = int(data.split("_")[2])
        user_id = query.from_user.id
        favorites = await db_service.get_favorites(user_id)
        fav = next((f for f in favorites if f["id"] == fav_id), None)
        if fav:
            await _send_place_radar(
                query.message, context, fav["lat"], fav["lon"], fav["name"], show_add_fav=False
            )
        else:
            await query.message.reply_text("❌ 找不到此喜愛點，可能已被刪除。")

    elif data.startswith("fav_d_"):
        fav_id = int(data.split("_")[2])
        user_id = query.from_user.id
        await db_service.delete_favorite(fav_id, user_id)
        favorites = await db_service.get_favorites(user_id)
        try:
            if not favorites:
                await query.edit_message_text("⭐ 喜愛點已全部清空。")
            else:
                await query.edit_message_text(
                    f"⭐ *我的喜愛點*（{len(favorites)}/{db_service.MAX_FAVORITES}）\n\n點選地點查詢即時雨勢，或按 🗑️ 刪除。",
                    parse_mode="Markdown",
                    reply_markup=_build_fav_keyboard(favorites),
                )
        except Exception:
            await query.message.reply_text("🗑️ 已刪除。")
        await query.answer("已刪除 ✓")

    elif data == "inbox_delete":
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


async def handle_region_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if context.user_data.get("awaiting_feedback_delete"):
        if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
            return
        ids = context.user_data.get("inbox_feedback_ids", [])
        try:
            num = int(text.strip())
            if not (1 <= num <= len(ids)):
                await update.message.reply_text(f"❌ 請輸入 1 到 {len(ids)} 之間的數字。")
                return
            context.user_data["awaiting_feedback_delete"] = False
            await db_service.delete_feedback_item(ids[num - 1])
            feedbacks = await db_service.get_all_feedback()
            context.user_data["inbox_feedback_ids"] = [fb["id"] for fb in feedbacks]
            if not feedbacks:
                await update.message.reply_text("📭 所有回饋已清空。")
            else:
                msg, keyboard = _build_inbox_text_and_keyboard(feedbacks)
                await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)
        except ValueError:
            await update.message.reply_text("❌ 請輸入數字。")
        return

    if context.user_data.get("awaiting_feedback"):
        feedback_text = text.strip()
        context.user_data["awaiting_feedback"] = False
        if not feedback_text:
            await update.message.reply_text("回饋不能為空，請重新使用 /feedback 提交。")
            return
        user = update.effective_user
        await db_service.add_feedback(user.id, user.username or "", feedback_text)
        await update.message.reply_text("✅ 感謝你的回饋！我們會認真參考。")
        return

    if context.user_data.get("awaiting_fav_name"):
        fav_name = text.strip()
        last = context.user_data.get("last_place")
        context.user_data["awaiting_fav_name"] = False
        if not fav_name or not last:
            await update.message.reply_text("❌ 命名失敗，請重新查詢地點後再加入。")
            return
        user_id = update.effective_user.id
        result = await db_service.add_favorite(user_id, fav_name, last["lat"], last["lon"])
        if "error" in result:
            if result["error"] == "limit_exceeded":
                await update.message.reply_text(
                    f"❌ 最多只能儲存 {db_service.MAX_FAVORITES} 個喜愛點，請先刪除舊的（/fav）。"
                )
            else:
                await update.message.reply_text(f"「{fav_name}」已在喜愛點中。")
        else:
            await update.message.reply_text(f"⭐ 已將「{fav_name}」加入喜愛點！")
        return

    region_map = {"北部": "north", "中部": "central", "南部": "south"}
    if text in region_map:
        region_key = region_map[text]
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
        return

    if context.user_data.get("awaiting_place_input"):
        lat, lon, _, _ = resolve_place_to_latlon(text)
        if lat is None or lon is None:
            await update.message.reply_text(
                f"❌ 找不到「{text}」這個地點，請重新輸入更完整的地名（例如：台北101）。"
            )
            return
        context.user_data["awaiting_place_input"] = False
        await _send_place_radar(update.message, context, lat, lon, text)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_location = update.message.location
    lat = user_location.latitude
    lon = user_location.longitude
    processing_msg = await update.message.reply_text(
        "⏳ 正在產生雷達降雨圖，請稍候...",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        img_bytes, img_time_str, rain_desc = await radar_service.get_marked_radar(lat, lon)
        if img_bytes:
            rain_desc = rain_desc or "☀️ 目前無明顯降雨"
            await update.message.reply_photo(
                photo=img_bytes,
                caption=f"🕒 時間：{img_time_str}\n{rain_desc}",
            )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ 抱歉，目前無法取得氣象雷達圖資，請稍後再試。")
    except Exception as e:
        print(f"處理雷達圖發生錯誤: {e}")
        await processing_msg.edit_text("❌ 發生系統錯誤，請稍後再試。")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"[ERROR] 發生例外：{context.error}")


# ── 啟動 ─────────────────────────────────────────────────────────────

def run_tg_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TG_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("fav", fav_command))
    app.add_handler(CommandHandler("nearby", request_location))
    app.add_handler(CommandHandler("radar", radar_menu))
    app.add_handler(CommandHandler("place", request_place))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("inbox", inbox_command))
    app.add_handler(CommandHandler("manual", manual))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_region_text))
    app.add_error_handler(error_handler)

    print("--- 氣象機器人已在背景啟動 ---")
    app.run_polling(drop_pending_updates=True, stop_signals=None)


class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Weather Bot is awake!")

    def log_message(self, format, *args):
        pass


def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    print(f"--- 輕量喚醒伺服器已在 Port {port} 對外開放 ---")
    server.serve_forever()


if __name__ == "__main__":
    threading.Thread(target=run_tg_bot, daemon=True).start()
    run_dummy_server()
