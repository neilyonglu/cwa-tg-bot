import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- 1. 讀取金鑰 ---
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- 2. 機器人邏輯 ---

# 初始化快捷選單與背景任務
async def post_init(application: Application):
    commands = [
        BotCommand("nearby", "📍 查詢現在位置雨量"),
        BotCommand("radar", "📡 查詢區域雷達圖 (北中南)"),
    ]
    await application.bot.set_my_commands(commands)
    print("--- 左下角快捷選單已自動同步 ---")
    
    # 啟動背景雷達輪詢任務
    from services.radar_service import RadarService
    asyncio.create_task(RadarService.start_background_task())
    print("--- 背景雷達輪詢任務已啟動 ---")

# 請求位置授權按鈕
async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location_button = KeyboardButton(text="📍 發送目前位置", request_location=True)
    reply_markup = ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "請點擊下方按鈕，查詢當地的降雨資訊 🌤️",
        reply_markup=reply_markup
    )

# 區域雷達選單 (第一層：選擇區域)
async def radar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟦 北部雷達圖", callback_data="region_north"), 
         InlineKeyboardButton("🟩 中部雷達圖", callback_data="region_central")],
        [InlineKeyboardButton("🟧 南部雷達圖", callback_data="region_south")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("請選擇要查詢的區域：", reply_markup=reply_markup)

# 處理區域選擇，並顯示時間選擇選單 (第二層：選擇時間)
async def handle_region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # 必須回應 CallbackQuery 避免轉圈圈
    
    region = query.data.split("_")[1] # e.g. "north"
    
    # 將區域名稱轉換為中文顯示
    region_name_map = {"north": "北部", "central": "中部", "south": "南部"}
    region_zh = region_name_map.get(region, region)
    
    keyboard = [
        [InlineKeyboardButton("🖼️ 單張最新", callback_data=f"time_{region}_0")],
        [InlineKeyboardButton("⏳ 過去 5 分鐘", callback_data=f"time_{region}_5"),
         InlineKeyboardButton("⏳ 過去 10 分鐘", callback_data=f"time_{region}_10")],
        [InlineKeyboardButton("⏳ 過去 20 分鐘", callback_data=f"time_{region}_20"),
         InlineKeyboardButton("⏳ 過去 30 分鐘", callback_data=f"time_{region}_30")],
        [InlineKeyboardButton("⏳ 過去 40 分鐘", callback_data=f"time_{region}_40"),
         InlineKeyboardButton("⏳ 過去 50 分鐘", callback_data=f"time_{region}_50")],
        [InlineKeyboardButton("⏳ 過去 60 分鐘", callback_data=f"time_{region}_60")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"你選擇了【{region_zh}】\n請選擇要觀看的時間範圍（GIF 動畫）：", reply_markup=reply_markup)

# 處理時間選擇並產生 GIF
async def handle_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, region, minutes_str = query.data.split("_")
    minutes = int(minutes_str)
    
    region_name_map = {"north": "北部", "central": "中部", "south": "南部"}
    region_zh = region_name_map.get(region, region)
    
    # 修改原本的訊息為處理中
    time_text = "單張最新圖片" if minutes == 0 else f"過去 {minutes} 分鐘的動態 GIF"
    await query.edit_message_text(f"⏳ 正在產生【{region_zh}】{time_text}，這可能需要一點時間，請稍候...")
    
    try:
        from services.radar_service import RadarService
        service = RadarService()
        
        if minutes == 0:
            # 只拿單張
            img_bytes, img_time_str = await service.get_region_radar(region)
            if img_bytes:
                await query.message.reply_photo(
                    photo=img_bytes,
                    caption=f"📡 {region_zh}雷達圖\n🕒 時間：{img_time_str}"
                )
                await query.message.delete()
            else:
                await query.edit_message_text("❌ 無法取得該區域雷達圖，可能是資料尚未更新，請稍後再試。")
        else:
            # 產生 GIF
            result = service.generate_gif(region, minutes)
            if result:
                img_bytes, is_gif = result
                caption = f"📡 {region_zh}雷達動態圖 (過去 {minutes} 分鐘)" if is_gif else f"📡 {region_zh}雷達圖\n⚠️ 歷史圖片不足，回傳單張圖片。"
                
                import io
                if is_gif:
                    # 包裝成帶有檔名的 BytesIO，避免 Telegram 辨識為 application.octet-stream
                    gif_file = io.BytesIO(img_bytes)
                    gif_file.name = "radar_animation.gif"
                    await query.message.reply_animation(animation=gif_file, caption=caption)
                else:
                    img_file = io.BytesIO(img_bytes)
                    img_file.name = "radar_static.png"
                    await query.message.reply_photo(photo=img_file, caption=caption)
                    
                await query.message.delete()
            else:
                await query.edit_message_text("❌ 目前歷史圖片不足，無法合成。請等待機器人收集更多圖資後再試！")
                
    except Exception as e:
        print(f"處理區域雷達發生錯誤: {e}")
        await query.edit_message_text("❌ 發生系統錯誤，請稍後再試。")

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
    app.add_handler(CallbackQueryHandler(handle_region_callback, pattern="^region_"))
    app.add_handler(CallbackQueryHandler(handle_time_callback, pattern="^time_"))
    
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
