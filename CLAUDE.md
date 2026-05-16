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
    user_id               BIGINT PRIMARY KEY,
    username              TEXT,
    subscribed            BOOLEAN DEFAULT FALSE,    -- /subscribe 訂閱狀態
    last_notified_version TEXT,                     -- 上次收到的 UPDATE_MESSAGE 版本
    first_seen            TIMESTAMP DEFAULT NOW()
    -- 自動由 models.user._ensure_schema() 建立（CREATE TABLE + ALTER ADD COLUMN IF NOT EXISTS）
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

## 可用 Skills（給 Claude 用，作者勿動）

開工前先想想能不能套以下 skill，比硬上有結構。叫法：`/<name>` 或請我用 Skill 工具呼叫。

### 程式碼結構/品質類
| Skill | 用途 | 何時叫 |
|---|---|---|
| `plan` | 拆解需求為可驗收的小任務，輸出 `tasks/plan.md` 與 `tasks/todo.md` | 新功能、重構、跨多檔變更前 |
| `build` | 按 plan 逐項實作，每步驟驗證、保持可編譯 | plan 完成後實作階段 |
| `review` | 五軸 code review：correctness / readability / architecture / security / performance | 寫完一段功能想做品管 |
| `simplify` | 掃改動過的 code，找重複、可重用、可精簡之處 | build 完成想清理冗餘 |
| `debug` | 系統性除錯：reproduce → localize → reduce → fix root cause → guard | 出現 bug、行為不符預期 |
| `security` | 針對 OWASP Top 10、secrets、auth/authz、input validation 的安檢 | 部署前、處理使用者輸入後 |
| `grill-me` | 反向質問逼問計畫漏洞 | 想壓力測試自己的設計或我的提案 |
| `init` | 初始化或重建 CLAUDE.md | 結構大改、新 contributor 入坑 |

### 流程/自動化類
| Skill | 用途 |
|---|---|
| `schedule` | 建立 cron 排程，自動跑某個 Claude 任務 |
| `loop` | 在固定間隔重複跑某個 prompt（如每 5 分鐘巡 PR） |
| `update-config` | 改 `.claude/settings.json`，加 hook、permission、env 等 |
| `fewer-permission-prompts` | 掃 transcript 自動加 allowlist，少按確認鍵 |

### 不適用本專案
- `claude-api`（本專案沒用 Anthropic SDK）、`keybindings-help`、`statusline-setup`

## 廣播新功能的方式（版本化通知）

1. 編輯 [app.py](app.py) 頂層的兩個常數：
   - `CURRENT_VERSION`：例如改成 `"2026-06-01"`
   - `UPDATE_MESSAGE`：Markdown 內文
2. push → Render 自動部署 → `post_init` 啟動
3. 只發給 `subscribed = TRUE AND last_notified_version != CURRENT_VERSION` 的使用者
4. 訊息以 `disable_notification=True` 無聲發送（手機不會響）
5. 成功後該欄會被更新為 `CURRENT_VERSION`；同版本後續重啟（含 Render 自發性重啟）不會重發
