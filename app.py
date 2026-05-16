import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import BotCommand
from telegram.ext import Application, MessageHandler, filters
from models import user as user_model
from models import favorite as fav_model
import handlers.start as h_start
import handlers.location as h_location
import handlers.place as h_place
import handlers.favorites as h_fav
import handlers.radar as h_radar
import handlers.subscribe as h_subscribe
import handlers.admin as h_admin

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "6501701404")

# 改這兩個常數 → push → Render 部署 → 訂閱者收到無聲通知一次
# 同一個 CURRENT_VERSION 重複部署不會重發
CURRENT_VERSION = "v1.1"
UPDATE_MESSAGE = (
    "🎉 *降雨機器人更新了！*\n\n"
    "✨ *最新功能：*\n"
    "• 🤖 AI 降雨分析：每次查詢自動解讀雷達數據，提供更直觀的降雨描述\n"
    "• ⭐ 喜愛點自訂名稱：儲存地點時可取名為「公司」、「家」等\n"
    "• 🔔 訂閱通知：使用 /subscribe 管理新功能通知設定\n\n"
    "輸入 /start 查看完整功能選單 🌦"
)

BOT_COMMANDS = [
    BotCommand("start", "🌦 開始使用"),
    BotCommand("nearby", "📍 查詢現在位置雨量"),
    BotCommand("place", "🔎 輸入地點查雨勢"),
    BotCommand("fav", "⭐ 我的喜愛點"),
    BotCommand("radar", "📡 查詢區域雷達圖"),
    BotCommand("subscribe", "🔔 訂閱／取消訂閱更新通知"),
    BotCommand("feedback", "💬 提供回饋"),
    BotCommand("manual", "📖 使用說明書"),
]


async def post_init(application: Application):
    await application.bot.set_my_commands(BOT_COMMANDS)
    await user_model._ensure_schema()
    await fav_model._ensure_schema()
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

    pending = await user_model.get_pending_subscribers(CURRENT_VERSION)
    print(f"--- 待通知訂閱者：{len(pending)} 位（版本 {CURRENT_VERSION}）---")
    sent_uids: list[int] = []
    for uid in pending:
        try:
            await application.bot.send_message(
                chat_id=uid,
                text=UPDATE_MESSAGE,
                parse_mode="Markdown",
                disable_notification=True,
            )
            sent_uids.append(uid)
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"--- 廣播給 {uid} 失敗：{e} ---")
    await user_model.mark_version_notified(sent_uids, CURRENT_VERSION)
    print(f"--- 廣播完成：{len(sent_uids)}/{len(pending)} ---")


async def _handle_text(update, context):
    handlers_with_text = [
        h_admin.handle_text,
        h_fav.handle_text,
        h_place.handle_text,
        h_radar.handle_text,
    ]
    for handler in handlers_with_text:
        if await handler(update, context):
            return


async def error_handler(update: object, context):
    print(f"[ERROR] 發生例外：{context.error}")


def run_tg_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TG_TOKEN).post_init(post_init).build()

    h_start.register(app)
    h_location.register(app)
    h_place.register(app)
    h_fav.register(app)
    h_radar.register(app)
    h_subscribe.register(app)
    h_admin.register(app)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_text))
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
