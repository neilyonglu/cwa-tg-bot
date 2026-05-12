# 氣象雷達機器人 (CWA Weather Telegram Bot)

一個專為 Telegram 設計的氣象機器人，串接中央氣象署 (CWA) 即時雷達圖資，提供台灣各地精準降雨查詢。

## 核心功能

- **GPS 即時雨勢**：發送目前位置，自動分析當地降雨強度並標註在雷達圖上
- **地點搜尋**：輸入地名，透過 Google Maps 定位後查詢即時雨勢
- **區域雷達圖**：一鍵查看北部、中部、南部大範圍雷達圖
- **喜愛點**：儲存最多 5 個自訂名稱的常用地點，一鍵查詢
- **AI 降雨分析**：每次查詢由 Gemini 自動解讀雷達數據，提供更直觀的降雨描述
- **訂閱通知**：訂閱後，伺服器有新功能時會主動通知
- **使用者回饋**：讓使用者提交意見，管理員可透過 `/inbox` 查看與刪除

## 技術堆疊

- **語言**：Python 3.12+
- **Telegram 框架**：`python-telegram-bot` >= 20.0
- **地理投影**：`pyproj`（WGS84 → AEQD 等距方位投影）
- **影像處理**：`Pillow`
- **地點解析**：Google Maps Geocoding API
- **AI 分析**：Google Gemini API（`gemini-3.1-flash-lite`）
- **資料庫**：PostgreSQL（Neon）via `psycopg2`

## 專案結構

```
cwa-tg-bot/
├── app.py                    # 主程式（啟動、post_init、文字訊息分發）
├── handlers/
│   ├── start.py              # /start、/manual
│   ├── location.py           # /nearby、GPS 位置處理
│   ├── place.py              # /place、地名解析
│   ├── favorites.py          # /fav、喜愛點管理
│   ├── radar.py              # /radar、區域雷達圖
│   ├── subscribe.py          # /subscribe、訂閱切換
│   └── admin.py              # /feedback、/inbox、管理員操作
├── models/
│   ├── user.py               # users 表（訂閱、使用者追蹤）
│   ├── favorite.py           # user_favorites 表
│   └── feedback.py           # feedback 表
├── services/
│   ├── radar_service.py      # 雷達圖orchestrator
│   ├── radar_fetch.py        # CWA S3 圖資下載與快取
│   ├── radar_render.py       # 座標轉換、像素分析、圖片標註
│   ├── llm_rainfall.py       # Gemini AI 降雨分析
│   └── db_conn.py            # PostgreSQL 連線 context manager
├── config/
│   └── settings.py           # 雷達站座標、dBZ 色碼表等常數
└── requirements.txt
```

## 環境變數

| 變數 | 必填 | 說明 |
|------|------|------|
| `TELEGRAM_TOKEN` | ✅ | Bot token（BotFather 取得）|
| `DATABASE_URL` | ✅ | PostgreSQL 連線字串 |
| `GOOGLE_MAPS_KEY` | ✅ | Google Cloud API key（Maps Geocoding）|
| `GEMINI_API_KEY` | ✅ | Google AI Studio key（Gemini LLM 分析）|
| `ADMIN_CHAT_ID` | 可選 | 接收系統啟動通知的管理員 chat_id |
| `BROADCAST_MESSAGE` | 可選 | 設定後，啟動時廣播給所有訂閱使用者，發完應移除 |
| `PORT` | 可選 | HTTP keep-alive server 的 port（預設 10000）|

## 資料庫 Schema

資料庫 Schema 由 `post_init` 自動建立（`CREATE TABLE IF NOT EXISTS`），無需手動執行 SQL。

```sql
CREATE TABLE users (
    user_id    BIGINT PRIMARY KEY,
    username   TEXT,
    subscribed BOOLEAN DEFAULT FALSE,
    first_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_favorites (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    name       TEXT NOT NULL,
    lat        DOUBLE PRECISION NOT NULL,
    lon        DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE feedback (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    username   TEXT,
    text       TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 指令列表

| 指令 | 說明 |
|------|------|
| `/start` | 開始使用，顯示功能選單 |
| `/nearby` | 發送 GPS 位置查詢即時雨勢 |
| `/place` | 輸入地名或地址查詢雨勢 |
| `/radar` | 查看北/中/南部區域雷達圖 |
| `/fav` | 管理我的喜愛點（最多 5 個）|
| `/subscribe` | 訂閱／取消訂閱新功能通知 |
| `/feedback` | 提交回饋給管理員 |
| `/manual` | 使用說明書 |
| `/inbox` | 查看所有回饋（僅管理員）|

## 廣播新功能的方式

1. 在部署環境設定 `BROADCAST_MESSAGE=<訊息內容>`
2. 重啟服務 → bot 啟動時自動發送給所有已訂閱使用者
3. 移除 `BROADCAST_MESSAGE` 環境變數（避免下次重啟重複發送）

建議訊息格式：
```
🎉 氣象機器人更新了！

✨ 新功能：
• 🤖 AI 降雨分析：每次查詢自動以 AI 解讀雷達數據
• ⭐ 喜愛點自訂名稱：可取名為「公司」、「家」等
• 🔔 訂閱通知：使用 /subscribe 管理通知設定

/start 查看完整功能
```

## 本地開發

```bash
cp .env.example .env  # 填入所有必要環境變數
python app_local.py   # polling 模式，不需 HTTP server
```

## 雲端部署（Render）

1. 將程式碼推送到 GitHub
2. Render Dashboard → **New → Web Service** → 匯入專案
3. 設定：
   - **Build Command**：`pip install -r requirements.txt`
   - **Start Command**：`python app.py`
4. 在 **Environment Variables** 加入所有必要環境變數
5. Deploy

部署後內建的 HTTP 伺服器會綁定 Render 提供的 Port，可搭配 Cron-job 定期喚醒。
