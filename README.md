# ⚡️ 氣象機器人 (CWA Weather Telegram Bot)

這是一個專為 Telegram 設計的自動化氣象機器人，能透過使用者發送的「目前位置」，即時從中央氣象署 (CWA) 獲取最新的雷達回波圖，並精準標註使用者所在的地理位置。

## 🚀 核心功能
*   **📍 精準雷達標註**：透過強大的 AEQD (Azimuthal Equidistant, 等距方位投影) 演算法，將使用者的經緯度完美映射至氣象署的雷達影像上，精準度極高。
*   **🛰️ 動態區域切換**：自動判斷使用者所在的緯度，智慧切換並下載北、中、南區最適合的雷達圖資。
*   **☁️ S3 雲端直連**：直接串接 CWA 開放資料的 Amazon S3 儲存桶，避開 API 速率限制與 404 問題，並內建記憶體快取 (Cache) 提升效能。
*   **🤖 自動化快捷選單**：登入後自動在左下角建立「📍 目前位置」按鈕，使用者操作零門檻。
*   **🌐 雲端部署就緒**：完全相容於 Render 等雲端平台，並內建輕量級 HTTP 伺服器 (供 UptimeRobot 喚醒)。

## 🛠️ 技術堆疊
*   **程式語言**：Python 3.12+
*   **Telegram 框架**：`python-telegram-bot` (v21)
*   **地理空間投影**：`pyproj` (用於高精度的 WGS84 轉 AEQD 投影)
*   **影像處理**：`Pillow` (裁切影像與繪製標記)

## 📂 專案結構
```text
cwa-tg-bot/
├── app.py                   # Telegram Bot 主程式 (背景執行 Bot + HTTP 伺服器)
├── app_local.py             # 本地測試腳本 (無需 Telegram，直接測試雷達圖與座標標註)
├── config/
│   └── settings.py          # 參數設定區 (雷達站座標、圖資來源、標記樣式與大小)
├── services/
│   └── radar_service.py     # 核心服務 (從 S3 抓取圖資、AEQD 投影轉換、Pillow 畫圖)
├── output/                  # app_local.py 產生的測試圖片目錄
├── requirements.txt         # 依賴套件清單
└── .env                     # 環境變數 (需自行建立)
```

## 📦 安裝與執行

### 1. 安裝相依套件
請使用 Conda 或 venv 建立虛擬環境後，執行以下指令：
```bash
pip install -r requirements.txt
```

### 2. 環境變數設定
在專案根目錄建立一個 `.env` 檔案，並填入你的 Telegram Bot 金鑰：
```env
TELEGRAM_TOKEN=你的_TELEGRAM_BOT_TOKEN
```

### 3. 本地端測試 (推薦)
如果你想先確認雷達圖是否能成功下載、標註位置是否精準，可以執行本地測試腳本。這不會啟動 Telegram Bot，而是將測試結果存入 `output/` 資料夾中。
```bash
python app_local.py
```

### 4. 啟動 Telegram 機器人
確認 `.env` 設定完畢後，直接執行主程式即可在終端機看到啟動訊息。
```bash
python app.py
```
打開你的 Telegram，找到你的機器人並點擊左下角的「📍 發送目前位置」即可看到結果！

## ☁️ 雲端部署 (Render)
1.  將程式碼推送到 GitHub。
2.  在 Render Dashboard 選擇 **New -> Web Service**。
3.  匯入你的 GitHub 專案。
4.  **設定指令**：
    *   **Build Command**：`pip install -r requirements.txt`
    *   **Start Command**：`python app.py`
5.  在 **Environment Variables** 區塊中新增 `TELEGRAM_TOKEN` 金鑰。
6.  點擊 Deploy。部署完成後，內建的 Web Server 會綁定 Render 提供的 Port 確保服務持續運行。
