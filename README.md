# 氣象雷達機器人 (CWA Weather Telegram Bot)

一個專為 Telegram 設計的氣象機器人，串接中央氣象署 (CWA) 即時雷達圖資，提供台灣各地精準降雨查詢。

## 核心功能

- **GPS 即時雨勢**：發送目前位置，自動分析當地降雨強度並標註在雷達圖上
- **地點搜尋**：輸入地名，透過 Google Maps 定位後查詢即時雨勢
- **區域雷達圖**：一鍵查看北部、中部、南部大範圍雷達圖
- **喜愛點**：儲存最多 5 個常用地點，一鍵查詢
- **使用者回饋**：讓使用者提交意見，管理員可透過 `/inbox` 查看與刪除

## 技術堆疊

- **語言**：Python 3.12+
- **Telegram 框架**：`python-telegram-bot` >= 20.0
- **地理投影**：`pyproj`（WGS84 → AEQD 等距方位投影）
- **影像處理**：`Pillow`
- **地點解析**：Google Maps Geocoding API
- **資料庫**：PostgreSQL（Neon）via `psycopg2`

## 專案結構

```
cwa-tg-bot/
├── app.py                 # 主程式（Telegram Bot + HTTP 喚醒伺服器）
├── config/
│   └── settings.py        # 常數設定（雷達站座標、dBZ 色碼表等）
├── services/
│   ├── radar_service.py   # 雷達圖抓取、座標轉換、圖片標註
│   └── db_service.py      # 資料庫操作（喜愛點、使用者回饋）
└── requirements.txt
```

## 環境變數

在專案根目錄建立 `.env`：

```env
TELEGRAM_TOKEN=你的_Telegram_Bot_Token
GEMINI_API_KEY=你的_Google_Maps_API_Key
DATABASE_URL=你的_PostgreSQL_連線字串
ADMIN_CHAT_ID=你的_Telegram_使用者_ID
```

## 資料庫初始化

在 PostgreSQL 執行以下 SQL：

```sql
CREATE TABLE user_favorites (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    name       TEXT NOT NULL,
    lat        DOUBLE PRECISION NOT NULL,
    lon        DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE feedback (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    username   TEXT,
    text       TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 指令列表

| 指令 | 說明 |
|------|------|
| `/start` | 開始使用，顯示功能選單 |
| `/nearby` | 發送 GPS 位置查詢即時雨勢 |
| `/place` | 輸入地名或地址查詢雨勢 |
| `/radar` | 查看北/中/南部區域雷達圖 |
| `/fav` | 管理我的喜愛點 |
| `/feedback` | 提交回饋給管理員 |
| `/manual` | 使用說明 |
| `/inbox` | 查看所有回饋（僅管理員）|

## 雲端部署（Render）

1. 將程式碼推送到 GitHub
2. Render Dashboard → **New → Web Service** → 匯入專案
3. 設定：
   - **Build Command**：`pip install -r requirements.txt`
   - **Start Command**：`python app.py`
4. 在 **Environment Variables** 加入上述四個環境變數
5. Deploy

部署後內建的 HTTP 伺服器會綁定 Render 提供的 Port，可搭配 Cron-job 定期喚醒。
