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
        BotCommand("current_location", "📍 目前位置"),
    ]
    await application.bot.set_my_commands(commands)
    print("--- 左下角快捷選單已自動同步 ---")

# 請求位置授權按鈕
async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location_button = KeyboardButton(text="📍 發送目前位置", request_location=True)
    reply_markup = ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "請點擊下方按鈕，讓我幫你查詢當地的氣象資訊 🌤️",
        reply_markup=reply_markup
    )

from services.radar_service import RadarService

# 接收並處理座標
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_location = update.message.location
    lat = user_location.latitude
    lon = user_location.longitude
    
    # 1. 先回覆處理中訊息
    processing_msg = await update.message.reply_text(
        "⏳ 正在為您產生精準的雷達降雨標註圖，請稍候...",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        # 2. 呼叫雷達服務產圖
        service = RadarService()
        img_bytes, station_name = service.get_marked_radar(lat, lon)

        if img_bytes:
            # 3. 發送圖片
            await update.message.reply_photo(
                photo=img_bytes,
                caption=f"✅ 標註完成！\n📡 使用雷達站：{station_name}\n📍 您的座標：({lat:.4f}, {lon:.4f})"
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
    
    app.add_handler(CommandHandler("current_location", request_location))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    
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
