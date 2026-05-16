import asyncio
import sys
import os
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()  # 必須在任何讀 env 的 module（services.db_conn）import 之前呼叫

from config.settings import RADAR_STATIONS
from services.radar_service import RadarService
from services.radar_fetch import fetch_radar_image
from services import llm_service
from models.radar_frame import (
    _ensure_schema as _ensure_radar_schema,
    save_frame,
    get_recent_frames,
    trim_keep_n,
)

BUFFER_INTERVAL_SEC = 360  # 6 min
BUFFER_KEEP_N = 5

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_KEY")
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


async def radar_buffer_loop():
    while True:
        for station_key, station in RADAR_STATIONS.items():
            try:
                img_bytes, img_time_str = await fetch_radar_image(
                    station["dataset_id"], force_refresh=True
                )
                if not img_bytes or img_time_str == "未知時間":
                    print(f"[buffer] {station_key}: skip (no data / no timestamp)")
                    continue
                img_time = datetime.strptime(img_time_str, "%Y-%m-%d %H:%M")
                inserted = await save_frame(station_key, img_time, img_bytes)
                trimmed = await trim_keep_n(station_key, keep=BUFFER_KEEP_N)
                total = len(await get_recent_frames(station_key, limit=BUFFER_KEEP_N + 5))
                tag = "NEW" if inserted else "DEDUP"
                print(
                    f"[buffer] {station_key} {img_time:%Y-%m-%d %H:%M} {tag}"
                    f" (trimmed {trimmed}, total {total})"
                )
            except Exception as exc:
                print(f"[buffer] {station_key}: error {exc!r}")
        print(f"[buffer] sleeping {BUFFER_INTERVAL_SEC}s ...")
        await asyncio.sleep(BUFFER_INTERVAL_SEC)


async def main():
    if "--buffer" in sys.argv:
        print(f"[buffer] starting — interval {BUFFER_INTERVAL_SEC}s, keep {BUFFER_KEEP_N}/station")
        await _ensure_radar_schema()
        await radar_buffer_loop()
        return

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

        print("\n--- LLM 分析 ---")
        llm_desc = await llm_service.analyze_rainfall(display_name, img_time, rain_desc)
        if llm_desc:
            print(f"LLM: {llm_desc}")
        else:
            print("LLM 分析失敗或未設定 GEMINI_API_KEY")
    else:
        print("Failed to get image bytes.")

if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    asyncio.run(main())
