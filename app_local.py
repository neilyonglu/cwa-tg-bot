import asyncio
from services.radar_service import RadarService

async def main():
    service = RadarService()
    # Test nearby with Taipei 101 coordinates
    lat = 25.033964
    lon = 121.564468
    print(f"Testing get_marked_radar with {lat}, {lon}...")
    img_bytes, img_time, rain_desc = await service.get_marked_radar(lat, lon)
    if img_bytes:
        print(f"Success! Time: {img_time}, Rain: {rain_desc}, Bytes: {len(img_bytes)}")
        with open("output/test_nearby.png", "wb") as f:
            f.write(img_bytes)
        print("Saved to output/test_nearby.png")
    else:
        print("Failed to get image bytes.")

if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    asyncio.run(main())
