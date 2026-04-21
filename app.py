import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer  # 🌟 內建極輕量伺服器套件
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

# 接收並處理座標
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_location = update.message.location
    lat = user_location.latitude
    lon = user_location.longitude
    
    await update.message.reply_text(
        f"✅ 成功接收座標！\n緯度：{lat}\n經度：{lon}\n\n(接下來我們會把這個座標拿去轉成行政區)",
        reply_markup=ReplyKeyboardRemove()
    )

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
