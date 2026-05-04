# ⚡️ 氣象機器人 (Weather Telegram Bot)

這是一個專為 Telegram 設計的自動化氣象機器人。它能夠接收使用者發送的「目前位置」，並回傳當地的天氣預報資訊。

![Demo Image](screenshots/demo_weather_bot.png)

## 🚀 核心功能
*   **📍 位置授權**：透過 Telegram 內建的「發送目前位置」按鈕，安全、快速地獲取使用者座標。
*   **🤖 自動化快捷選單**：登入後自動在左下角建立「📍 目前位置」快捷按鈕，使用者無需記住指令。
*   **💬 智能回覆**：接收座標後，立即回傳處理結果 (未來可擴展為真實天氣預報)。
*   **🌐 雲端部署就緒**：完全相容於 Render、Fly.io 等雲端平台，並內建輕量級 Pinger (Pingdom/UptimeRobot 適用)。

## 🛠️ 技術堆疊
*   **程式語言**：Python 3.12+
*   **Telegram 框架**：`python-telegram-bot` (v21)
*   **部署環境**：Render (使用 `app.py` 及 Procfile 部署)
*   **環境變數**：`TELEGRAM_TOKEN`

## 📦 安裝與執行

### 1. 安裝相依套件
```bash
pip install -r requirements.txt
```

### 2. 本地端測試 (使用 `app_local.py`)
你可以直接使用 `app_local.py` 來進行核心邏輯的測試，無需 Telegram 帳號。
```bash
python app_local.py
```

### 3. 雲端部署 (使用 `app.py`)
請確保你的專案根目錄包含 `Procfile` 和 `app.py`。
*   **Procfile** 指示 Render 在启动时运行 `web: python app.py`。
*   **app.py** 包含整合 Telegram 機器人與輕量 HTTP 伺服器的完整程式碼。

### 4. 啟用 Render 部署 (手動步驟)
1.  在 GitHub 上推送你的程式碼。
2.  登入 Render Dashboard。
3.  選擇 **New -> Web Service**。
4.  選擇 **Import from GitHub**，並選取你的程式碼。
5.  **重要設定**：
    *   **Build Command**：`pip install -r requirements.txt`
    *   **Start Command**：`python app.py`
6.  在 **Environment** 中新增你的金鑰 `TELEGRAM_TOKEN`。
7.  點擊 **Create Web Service**。
