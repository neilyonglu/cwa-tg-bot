import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- 1. 讀取金鑰 ---
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- 2. 機器人邏輯 ---

# 初始化快捷選單
async def post_init(application: Application):
    commands = [
        BotCommand("nearby", "📍 查詢現在位置雨量"),
        BotCommand("radar", "📡 查詢區域雷達圖 (北中南)"),
    ]
    await application.bot.set_my_commands(commands)
    print("--- 左下角快捷選單已自動同步 ---")
    
    # 部署完成後，自動發送更新通知給管理員
    admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "6501701404")
    try:
        update_msg = (
            "🚀 **系統更新完成！**\n\n"
        )
        await application.bot.send_message(chat_id=admin_chat_id, text=update_msg, parse_mode="Markdown")
        print(f"--- 已發送系統更新通知給 {admin_chat_id} ---")
    except Exception as e:
        print(f"--- 無法發送更新通知給管理員: {e} ---")

# 請求位置授權按鈕
async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location_button = KeyboardButton(text="📍 發送目前位置", request_location=True)
    reply_markup = ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "請點擊下方按鈕，查詢當地的降雨資訊 🌤️",
        reply_markup=reply_markup
    )

# 區域雷達選單
async def radar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🟦 北部雷達圖"), KeyboardButton("🟩 中部雷達圖")],
        [KeyboardButton("🟧 南部雷達圖")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("請選擇要查詢的區域：", reply_markup=reply_markup)

# 處理區域選擇
async def handle_region_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    region_map = {
        "🟦 北部雷達圖": "north",
        "🟩 中部雷達圖": "central",
        "🟧 南部雷達圖": "south"
    }
    
    if text not in region_map:
        return # 不處理非按鈕文字
        
    region_key = region_map[text]
    processing_msg = await update.message.reply_text(f"⏳ 正在抓取{text}，請稍候...", reply_markup=ReplyKeyboardRemove())
    
    try:
        from services.radar_service import RadarService
        service = RadarService()
        img_bytes, img_time_str = await service.get_region_radar(region_key)
        
        if img_bytes:
            await update.message.reply_photo(
                photo=img_bytes,
                caption=f"📡 {text}\n🕒 時間：{img_time_str}"
            )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ 無法取得該區域雷達圖，請稍後再試。")
    except Exception as e:
        print(f"處理區域雷達發生錯誤: {e}")
        await processing_msg.edit_text("❌ 發生系統錯誤，請稍後再試。")

# 接收並處理座標
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_location = update.message.location
    lat = user_location.latitude
    lon = user_location.longitude
    
    # 1. 先回覆處理中訊息
    processing_msg = await update.message.reply_text(
        "⏳ 正在產生雷達降雨圖，請稍候...",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        # 2. 呼叫雷達服務產圖
        service = RadarService()
        img_bytes, img_time_str = await service.get_marked_radar(lat, lon)

        if img_bytes:
            # 3. 發送圖片
            await update.message.reply_photo(
                photo=img_bytes,
                caption=f"🕒 時間：{img_time_str}"
            )
            # 刪除處理中訊息
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ 抱歉，目前無法取得氣象雷達圖資，請稍後再試。")
            
    except Exception as e:
        print(f"處理雷達圖發生錯誤: {e}")
        await processing_msg.edit_text("❌ 發生系統錯誤，請稍後再試。")

# --- 3. 機器人啟動器 ---
def run_tg_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app = Application.builder().token(TG_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("nearby", request_location))
    app.add_handler(CommandHandler("radar", radar_menu))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_region_text))
    
    print("--- 氣象機器人已在背景啟動 ---")
    app.run_polling(drop_pending_updates=True, stop_signals=None)


# --- 4. 🌟 極輕量網頁伺服器 (給 Render 與 UptimeRobot 喚醒用) ---
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Weather Bot is awake!")
        
    def log_message(self, format, *args):
        pass  # 關閉網頁請求日誌，保持終端機乾淨

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), PingHandler)
    print(f"--- 輕量喚醒伺服器已在 Port {port} 對外開放 ---")
    server.serve_forever()

# --- 5. 主程式入口 ---
if __name__ == "__main__":
    # 讓 Telegram 機器人在背景獨立運作
    threading.Thread(target=run_tg_bot, daemon=True).start()
    
    # 讓輕量伺服器在主程式運作，滿足 Render 的 Port 綁定需求
    run_dummy_server()
