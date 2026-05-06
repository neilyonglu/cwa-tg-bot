import asyncio
import sys
import requests
from services.radar_service import RadarService

GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
PLACE_FALLBACKS = {
    "台北101": (25.033964, 121.564468),
    "taipei 101": (25.033964, 121.564468),
}


def resolve_place_to_latlon(place_name: str):
    """將地點文字轉成經緯度。優先 geocoding，失敗時用本地 fallback。"""
    query = (place_name or "").strip() or "台北101"

    try:
        response = requests.get(
            GEOCODE_URL,
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "tw",
            },
            headers={"User-Agent": "cwa-tg-bot-local-test/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        results = response.json()
        if results:
            first = results[0]
            lat = float(first["lat"])
            lon = float(first["lon"])
            display_name = first.get("display_name", query)
            return lat, lon, display_name, "geocoding"
    except Exception as exc:
        print(f"[Geocoding 失敗] {exc}")

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
