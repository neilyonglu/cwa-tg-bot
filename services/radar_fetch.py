import time
import asyncio
import requests
from datetime import datetime
from config.settings import CACHE_TTL, CWA_S3_BASE_URL

_cache: dict = {}  # {dataset_id: (image_bytes, timestamp, img_time_str)}


async def fetch_radar_image(dataset_id: str, force_refresh: bool = False):
    if not force_refresh and dataset_id in _cache:
        img_bytes, timestamp, img_time_str = _cache[dataset_id]
        if time.time() - timestamp < CACHE_TTL:
            print(
                f"  [快取命中] {dataset_id} (已快取 {time.time() - timestamp:.0f} 秒)"
            )
            return img_bytes, img_time_str

    try:
        s3_img_url = f"{CWA_S3_BASE_URL}/{dataset_id}.png"
        s3_json_url = f"{CWA_S3_BASE_URL}/{dataset_id}.json"

        print(f"  [S3] 下載 {s3_img_url}")
        loop = asyncio.get_running_loop()
        img_response = await loop.run_in_executor(None, requests.get, s3_img_url)
        img_response.raise_for_status()
        img_bytes = img_response.content

        img_time_str = "未知時間"
        try:
            json_response = await loop.run_in_executor(None, requests.get, s3_json_url)
            if json_response.status_code == 200:
                data = json_response.json()
                dt_str = data["cwaopendata"]["dataset"]["DateTime"]
                img_time_str = datetime.fromisoformat(dt_str).strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            print(f"  [時間解析失敗] {e}")

        _cache[dataset_id] = (img_bytes, time.time(), img_time_str)
        return img_bytes, img_time_str

    except Exception as e:
        print(f"  [S3 失敗] {e}")
        return None, None
