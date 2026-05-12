# CWA Telegram Bot

即時降雨查詢 Telegram Bot，串接中央氣象署 (CWA) 雷達圖資。

## 架構

```
app.py              — Bot 主程式（handlers、啟動）
services/
  radar_service.py  — 下載 CWA S3 雷達圖、像素分析、座標轉換
  llm_service.py    — Gemini API 降雨文字分析
  db_service.py     — PostgreSQL CRUD（喜愛點、回饋、使用者追蹤）
config/
  settings.py       — 雷達站定義、圖像常數、dBZ 色碼表
```

## 環境變數

| 變數 | 必填 | 說明 |
|---|---|---|
| `TELEGRAM_TOKEN` | ✅ | Bot token（BotFather 取得）|
| `DATABASE_URL` | ✅ | PostgreSQL 連線字串 |
| `GOOGLE_MAPS_KEY` | ✅ | Google Cloud API key（用於 Maps Geocoding 地址解析）|
| `GEMINI_API_KEY` | ✅ | Google AI Studio API key（用於 Gemini LLM 降雨分析）|
| `ADMIN_CHAT_ID` | 可選 | 接收系統啟動通知的管理員 chat_id（預設 6501701404）|
| `BROADCAST_MESSAGE` | 可選 | 設定後，bot 啟動時會廣播此訊息給所有追蹤使用者；發完後應移除此變數避免重複傳送 |
| `PORT` | 可選 | HTTP keep-alive server 的 port（預設 10000，Render 部署用）|

## 資料庫 Schema

```sql
-- 喜愛點
CREATE TABLE user_favorites (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    name       TEXT NOT NULL,
    lat        DOUBLE PRECISION NOT NULL,
    lon        DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 使用者回饋
CREATE TABLE feedback (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    username   TEXT,
    text       TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 使用者追蹤（廣播用）
CREATE TABLE users (
    user_id    BIGINT PRIMARY KEY,
    username   TEXT,
    first_seen TIMESTAMP DEFAULT NOW()
    -- 自動由 db_service.save_user() 建立（CREATE TABLE IF NOT EXISTS）
);
```

## 本地開發

```bash
cp .env.example .env  # 填入 TELEGRAM_TOKEN, DATABASE_URL, GEMINI_API_KEY
python app_local.py   # 使用 polling 模式，不需 HTTP server
```

## 部署（Render）

- 執行指令：`python app.py`
- 服務同時跑兩個 thread：Telegram polling + HTTP keep-alive server（避免 Render 休眠）

## 雷達圖資

- 來源：CWA S3 `cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/`
- 三站：北部(樹林) `O-A0084-001`、中部(南屯) `O-A0084-002`、南部(林園) `O-A0084-003`
- 快取 TTL：5 分鐘
- 單站盲區時自動 fallback 到鄰站（`RADAR_BACKUP_ORDER`）

## 廣播新功能的方式

1. 部署環境設定 `BROADCAST_MESSAGE=<訊息內容>`
2. 重啟服務 → bot 啟動時自動發送給所有 `users` 表中的使用者
3. 移除 `BROADCAST_MESSAGE` 環境變數（避免下次重啟重複發送）
