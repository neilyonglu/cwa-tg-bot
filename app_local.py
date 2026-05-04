# app_local.py
"""
本地端測試腳本 - 不依賴 Telegram，直接驗證雷達圖標註功能。
產生的測試圖片會存放在 output/ 資料夾。
"""

import os
import sys
from services.radar_service import RadarService

# 修正 Windows 終端編碼問題
sys.stdout.reconfigure(encoding="utf-8")


def main():
    """基本測試：三個地標各自標註"""
    print("=== 基本標註測試 ===\n")

    os.makedirs("output", exist_ok=True)
    service = RadarService()

    test_locations = [
        # {"name": "台北101",   "lat": 25.0337, "lon": 121.5648},
        # {"name": "台中火車站", "lat": 24.1375, "lon": 120.6869},
        # {"name": "安平古堡",  "lat": 23.0016, "lon": 120.1606},
        {"name": "指定測試點1", "lat": 25.017292292773444, "lon": 121.99777287893849}
        
    ]

    for loc in test_locations:
        print(f"\n{'='*50}")
        print(f"測試地點：{loc['name']}")
        print(f"  座標 -> 緯度: {loc['lat']}, 經度: {loc['lon']}")

        img_bytes, station_name = service.get_marked_radar(loc["lat"], loc["lon"])

        if img_bytes:
            filename = f"output/radar_{loc['name']}.png"
            with open(filename, "wb") as f:
                f.write(img_bytes)
            print(f"成功！雷達站: {station_name}，已存檔: {filename}")
        else:
            print(f"失敗！無法取得 {loc['name']} 的雷達圖。")

    print(f"\n{'='*50}")
    print("完成！請查看 output/ 資料夾。")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
