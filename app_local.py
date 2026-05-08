import asyncio
import sys
import os
import requests
from dotenv import load_dotenv
from services.radar_service import RadarService

load_dotenv()

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_MAPS_API_KEY = os.environ.get("GEMINI_API_KEY")
PLACE_FALLBACKS = {
    "台北101": (25.033964, 121.564468),
    "taipei 101": (25.033964, 121.564468),
}


def resolve_place_to_latlon(place_name: str):
    query = (place_name or "").strip() or "台北101"

    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ 警告：未設定環境變數 GEMINI_API_KEY，將跳過 Google Maps 查詢。")
    else:
        try:
            response = requests.get(
                GOOGLE_GEOCODE_URL,
                params={
                    "address": query,
                    "key": GOOGLE_MAPS_API_KEY,
                    "language": "zh-TW",
                    "region": "tw"
                },
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                lat = float(result["geometry"]["location"]["lat"])
                lon = float(result["geometry"]["location"]["lng"])
                display_name = result.get("formatted_address", query)
                return lat, lon, display_name, "google"
            elif data.get("status") != "ZERO_RESULTS":
                print(f"[Google API 錯誤] Status: {data.get('status')}")
        except Exception as exc:
            print(f"[Google Geocoding 失敗] {exc}")

    fallback_key = query.lower()
    if fallback_key in PLACE_FALLBACKS:
        lat, lon = PLACE_FALLBACKS[fallback_key]
        return lat, lon, query, "fallback"

    return None, None, query, "not_found"


async def main():
    service = RadarService()
    if len(sys.argv) > 1:
        place_name = " ".join(sys.argv[1:]).strip()
    else:
        place_name = input("請輸入地點（例如：台北101）: ").strip() or "台北101"
    lat, lon, display_name, source = resolve_place_to_latlon(place_name)
    if lat is None or lon is None:
        print(f"找不到地點：{display_name}")
        if not GOOGLE_MAPS_API_KEY:
            print("💡 提示：設定 GEMINI_API_KEY 環境變數可大幅提升精準度。")
        return

    print(f"地點解析成功（{source}）：{display_name}")
    print(f"Testing get_marked_radar with {lat}, {lon}...")
    img_bytes, img_time, rain_desc = await service.get_marked_radar(lat, lon)
    if img_bytes:
        print(f"Success! Time: {img_time}, Rain: {rain_desc}, Bytes: {len(img_bytes)}")
        with open("output/test_place_radar.png", "wb") as f:
            f.write(img_bytes)
        print("Saved to output/test_place_radar.png")
    else:
        print("Failed to get image bytes.")

if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    asyncio.run(main())
