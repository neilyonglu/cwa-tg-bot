from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler
from models import user as user_model


async def start_command(update, context):
    user = update.effective_user
    await user_model.save_user(user.id, user.username or "")
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
        "即時查詢台灣各地降雨資訊，資料來源：中央氣象署 (CWA)。\n"
        "每次查詢均搭配 🤖 AI 自動分析降雨狀況。\n\n"
        "📍 `/nearby` — 查詢現在位置\n"
        "🔎 `/place` — 輸入地點查雨勢\n"
        "📡 `/radar` — 大區域雷達圖\n"
        "⭐ `/fav` — 我的喜愛點\n"
        "🔔 `/subscribe` — 訂閱新功能通知\n"
        "📖 `/manual` — 使用說明書"
    )
    await update.message.reply_text(
        msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def manual_command(update, context):
    msg = (
        "📖 **氣象雷達機器人 使用說明書**\n\n"
        "本機器人串接中央氣象署 (CWA) 即時圖資，提供精準的降雨趨勢查詢，"
        "並由 AI 自動分析每次查詢結果。\n\n"
        "📍 **功能介紹：**\n"
        "1. `/nearby` - **查詢目前位置**\n"
        "   發送你的 GPS 座標，機器人會回傳以你為中心的雷達圖，並自動分析降雨強度。\n\n"
        "2. `/place` - **查詢指定地點**\n"
        "   輸入地名或地址（例如：`台北101`），系統會精準定位並顯示當地即時雨勢。\n\n"
        "3. `/radar` - **大區域雷達圖**\n"
        "   快速切換查看「北部、中部、南部」的大範圍降雨分佈。\n\n"
        "4. `/fav` - **我的喜愛點**\n"
        "   儲存最多 5 個常用地點，可自訂名稱（例如：公司、家、學校），一鍵查詢即時雨勢。\n\n"
        "5. `/subscribe` - **訂閱新功能通知**\n"
        "   訂閱後，伺服器有新功能更新時會主動通知你。\n\n"
        "🤖 **AI 降雨分析：**\n"
        "• 每次查詢自動解讀雷達圖資，說明降雨強度與範圍。\n"
        "• 分析僅根據雷達圖資，不含氣溫、紫外線等其他資料。\n\n"
        "🖼️ **結果解讀：**\n"
        "• **紅色圓點**：代表你查詢的確切目標位置。\n"
        "• **彩色區塊**：代表降雨強度（綠色 < 藍色 < 黃色 < 紅色 < 紫色）。\n\n"
        "⚠️ **小提醒：**\n"
        "• 氣象署圖資約每 2-10 分鐘更新一次。\n"
        "• 若地點搜尋不到，請嘗試輸入更完整的行政區名稱。"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


def register(app):
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("manual", manual_command))
