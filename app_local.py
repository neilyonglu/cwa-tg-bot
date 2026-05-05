# app_local.py
"""
本地端測試腳本 - 驗證背景雷達輪詢與 GIF 動態圖合成功能。
產生的測試圖片/GIF 會存放在 output/ 資料夾。
"""

import os
import sys
import asyncio
from services.radar_service import RadarService

# 修正 Windows 終端編碼問題
sys.stdout.reconfigure(encoding="utf-8")

async def main():
    print("=== 背景雷達與 GIF 合成測試 ===\n")
    os.makedirs("output", exist_ok=True)

    # 1. 啟動背景任務 (不 await 它，讓它在背景執行)
    bg_task = asyncio.create_task(RadarService.start_background_task())

    print("請注意：官方雷達圖大約每 1分40秒 會更新一次。")
    print("此腳本會啟動背景任務，採用「發現新圖後等 90 秒，否則每 10 秒檢查一次」的邏輯。")
    print("因為等待時間設為 5 分鐘，結束時應該會收集到 3~4 張歷史圖片來合成 GIF。\n")

    # 讓背景任務持續執行 5 分鐘 (300秒)
    print("⏳ 開始等待 5 分鐘，這段期間背景任務會持續輪詢氣象署最新圖資...")
    for i in range(5):
        print(f"  已經過 {i} 分鐘...")
        await asyncio.sleep(60)
    print("  已經過 5 分鐘！開始合成 GIF...")

    print("\n--- 模擬使用者請求：北部雷達圖，過去 5 分鐘 ---")
    service = RadarService()
    
    # 測試產生 GIF
    result = service.generate_gif("north", 5)
    
    if result:
        img_bytes, is_gif = result
        ext = "gif" if is_gif else "png"
        filename = f"output/test_radar_animation.{ext}"
        
        with open(filename, "wb") as f:
            f.write(img_bytes)
            
        if is_gif:
            print(f"✅ 成功合成 GIF！已儲存至: {filename}")
        else:
            print(f"⚠️ 目前只有一張圖，無法合成 GIF，已儲存為靜態圖片: {filename}")
    else:
        print("❌ 產生失敗，可能是佇列中還沒有圖片。")

    print("\n測試結束 (背景任務即將關閉)。")
    bg_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("使用者中斷程式。")
