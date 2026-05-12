# CWA Telegram Bot

即時降雨查詢 Telegram Bot，串接中央氣象署 (CWA) 雷達圖資。

## 架構

```
app.py                    — 啟動、post_init、文字訊息分發（_handle_text）
handlers/
  start.py                — /start、/manual
  location.py             — /nearby、GPS 位置處理
  place.py                — /place、Google Maps 地名解析
  favorites.py            — /fav、喜愛點 CRUD
  radar.py                — /radar、區域雷達圖
  subscribe.py            — /subscribe、訂閱切換
  admin.py                — /feedback、/inbox、管理員刪除回饋
  _utils.py               — 共用：build_fav_keyboard、send_place_radar、RadarService singleton
models/
  user.py                 — users 表（save_user、toggle_subscription、get_subscribed_user_ids）
  favorite.py             — user_favorites 表（get/add/delete_favorite）
  feedback.py             — feedback 表（add/get_all/delete_feedback_item）
services/
  radar_service.py        — RadarService orchestrator（get_marked_radar、get_region_radar）
  radar_fetch.py          — CWA S3 圖資下載與快取（TTL 5 分鐘）
  radar_render.py         — 座標轉換、像素 dBZ 分析、圖片標註
  llm_rainfall.py         — Gemini AI 降雨分析（analyze_rainfall）
  llm_service.py          — re-export llm_rainfall（向後相容）
  db_conn.py              — PostgreSQL 連線 context manager（_db）
  db_service.py           — re-export models/*（向後相容）
config/
  settings.py             — 雷達站定義、圖像常數、dBZ 色碼表
```

## 環境變數

| 變數 | 必填 | 說明 |
|---|---|---|
| `TELEGRAM_TOKEN` | ✅ | Bot token（BotFather 取得）|
| `DATABASE_URL` | ✅ | PostgreSQL 連線字串 |
| `GOOGLE_MAPS_KEY` | ✅ | Google Cloud API key（Maps Geocoding 地址解析）|
| `GEMINI_API_KEY` | ✅ | Google AI Studio API key（Gemini LLM 降雨分析）|
| `ADMIN_CHAT_ID` | 可選 | 接收系統啟動通知的管理員 chat_id（預設 6501701404）|
| `BROADCAST_MESSAGE` | 可選 | 設定後廣播給所有訂閱使用者；設為 `1` 使用內建新功能通知；發完後移除 |
| `PORT` | 可選 | HTTP keep-alive server 的 port（預設 10000，Render 部署用）|

## 資料庫 Schema

Schema 由 `post_init` 呼叫 `_ensure_schema()` 自動建立，無需手動執行 SQL。

```sql
-- 使用者追蹤與訂閱
CREATE TABLE users (
    user_id    BIGINT PRIMARY KEY,
    username   TEXT,
    subscribed BOOLEAN DEFAULT FALSE,
    first_seen TIMESTAMP DEFAULT NOW()
);

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
```

## 本地開發

```bash
cp .env.example .env  # 填入所有必要環境變數
python app_local.py   # 使用 polling 模式，不需 HTTP server
```

conda env: `cwa`（`/home/neil/miniconda3/envs/cwa/`）

## 部署（Render）

- 執行指令：`python app.py`
- 服務同時跑兩個 thread：Telegram polling + HTTP keep-alive server（避免 Render 休眠）
- Render 有 cron 喚醒，不依賴 HTTP server 保活

## 雷達圖資

- 來源：CWA S3 `cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/`
- 三站：北部(樹林) `O-A0084-001`、中部(南屯) `O-A0084-002`、南部(林園) `O-A0084-003`
- 快取 TTL：5 分鐘
- 單站盲區時自動 fallback 到鄰站（`RADAR_BACKUP_ORDER` in settings.py）

## 廣播新功能的方式

1. 部署環境設定 `BROADCAST_MESSAGE=1`（使用內建新功能通知）或自訂訊息內容
2. 重啟服務 → bot 啟動時自動發送給所有 `subscribed=TRUE` 的使用者
3. 移除 `BROADCAST_MESSAGE` 環境變數（避免下次重啟重複發送）

注意：廣播對象是**有訂閱**的使用者（`subscribed = TRUE`），不是全部使用者。

## 文字訊息分發順序

`app.py` 的 `_handle_text` 依序嘗試各 handler 的 `handle_text(update, context) -> bool`：

1. `admin.handle_text` — 回饋刪除編號、回饋內容輸入
2. `favorites.handle_text` — 喜愛點命名輸入
3. `place.handle_text` — 地點查詢輸入
4. `radar.handle_text` — 區域關鍵字（北部／中部／南部）

第一個回傳 `True` 的 handler 即停止，其餘不執行。
