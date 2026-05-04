# app_local.py

def process_weather_data(lat, lon):
    """
    核心氣象邏輯處理區 (完全不依賴 Telegram)
    之後氣象署 API 串接、行政區轉換等邏輯都會寫在這裡。
    """
    
    # 這裡未來可以加入：
    # 1. 將經緯度轉換為縣市/鄉鎮市區 (例如透過 Google Maps API 或政府開放資料)
    # 2. 使用轉換後的行政區，去呼叫中央氣象署 (CWA) 的 API 取得天氣預報
    
    # 模擬資料處理的過程
    print(f"[系統提示] 正在處理座標 ({lat}, {lon}) 的氣象資料...")
    
    # 組合最後要回傳給使用者的文字
    result_text = (
        f"✅ 成功接收座標！\n"
        f"📍 緯度：{lat}\n"
        f"📍 經度：{lon}\n"
        f"\n"
        f"(此為本地端測試回傳的假天氣資訊，未來這裡會顯示真實氣象)"
    )
    
    return result_text


if __name__ == "__main__":
    # --- 本地端測試區 ---
    print("=== 氣象機器人本地端測試系統 ===")
    
    # 你指定的測試座標清單
    test_locations = [
        {"name": "台北101", "lat": 25.0330, "lon": 121.5654},
        {"name": "台中火車站", "lat": 24.1369, "lon": 120.6847},
        {"name": "安平古堡", "lat": 23.0011, "lon": 120.1605}
    ]
    
    for loc in test_locations:
        print(f"\n📍 目前測試地點：{loc['name']}")
        print(f"   使用的座標 -> 緯度: {loc['lat']}, 經度: {loc['lon']}")
        print("--- 機器人回覆內容 ---")
        
        # 呼叫核心邏輯並印出結果
        response = process_weather_data(loc['lat'], loc['lon'])
        print(response)
        
        print("----------------------")
    
    print("\n✅ 所有指定地點測試完畢！\n")
