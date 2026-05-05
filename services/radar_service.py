# services/radar_service.py
"""
降雨雷達圖資服務
- 從 CWA S3 抓取雷達回波圖
- 使用 AEQD (等距方位投影) 精準轉換經緯度 → 像素座標
- 在圖片上標註使用者位置並裁切回傳
"""

import requests
import time
import io
import asyncio
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

from config.settings import (
    RADAR_STATIONS,
    REGION_LAT_BOUNDARIES,
    IMAGE_SIZE,
    IMAGE_CENTER_PX,
    PIXEL_PER_KM,
    CACHE_TTL,
    CWA_S3_BASE_URL,
    MARKER_RADIUS,
    MARKER_COLOR,
    MARKER_OUTLINE,
    MARKER_OUTLINE_WIDTH,
    CROP_SIZE,
)


class RadarService:
    """降雨雷達圖資服務"""
    
    # 類別變數 (Class Variable)：讓所有 RadarService 實例共用同一個快取
    _cache = {}  # {dataset_id: (image_bytes, timestamp, img_time_str)}


    def __init__(self):
        pass

    # ─── 區域判斷 ─────────────────────────────────────────
    def get_station_for_location(self, lat, lon):
        """根據緯度自動判斷該使用哪一座雷達站"""
        if lat > REGION_LAT_BOUNDARIES["north"]:
            return RADAR_STATIONS["north"]
        elif lat > REGION_LAT_BOUNDARIES["central"]:
            return RADAR_STATIONS["central"]
        else:
            return RADAR_STATIONS["south"]

    # ─── 圖資取得 (S3) ────────────────────────────────────
    async def fetch_radar_image(self, dataset_id, force_refresh=False):
        """從 CWA S3 抓取雷達回波圖 (含快取機制)"""
        # 檢查快取
        if not force_refresh and dataset_id in self._cache:
            img_bytes, timestamp, img_time_str = self._cache[dataset_id]
            age = time.time() - timestamp
            if age < CACHE_TTL:
                print(f"  [快取命中] {dataset_id} (已快取 {age:.0f} 秒)")
                return img_bytes, img_time_str

        # 從 S3 抓取
        try:
            s3_img_url = f"{CWA_S3_BASE_URL}/{dataset_id}.png"
            s3_json_url = f"{CWA_S3_BASE_URL}/{dataset_id}.json"
            
            print(f"  [S3] 下載 {s3_img_url}")
            loop = asyncio.get_event_loop()
            img_response = await loop.run_in_executor(None, requests.get, s3_img_url)
            img_response.raise_for_status()

            img_bytes = img_response.content
            
            # 解析圖片產生時間 (從 S3 上的 JSON 取得官方時間)
            img_time_str = "未知時間"
            try:
                json_response = await loop.run_in_executor(None, requests.get, s3_json_url)
                if json_response.status_code == 200:
                    data = json_response.json()
                    dt_str = data["cwaopendata"]["dataset"]["DateTime"]
                    from datetime import datetime
                    dt = datetime.fromisoformat(dt_str)
                    img_time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception as e:
                print(f"  [時間解析失敗] {e}")

            self._cache[dataset_id] = (img_bytes, time.time(), img_time_str)
            return img_bytes, img_time_str

        except Exception as e:
            print(f"  [S3 失敗] {e}")
            return None, None

    # ─── 座標轉換 (AEQD 等距方位投影) ────────────────────
    def _latlon_to_pixel(self, center_lat, center_lon, user_lat, user_lon):
        """
        使用 AEQD (Azimuthal Equidistant) 投影，
        以雷達站為中心，將使用者經緯度精準轉換為像素座標。

        AEQD 的特性：從中心點出發的距離在所有方向上都是正確的，
        這與雷達的掃描方式完全吻合。
        """
        # 建立 WGS84 → AEQD 轉換器 (以雷達站為投影中心)
        transformer = Transformer.from_crs(
            "EPSG:4326",  # WGS84 (經緯度)
            f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} +datum=WGS84",
            always_xy=True,
        )

        # 轉換 → 得到以雷達站為原點的公尺座標 (x=東西, y=南北)
        x_meters, y_meters = transformer.transform(user_lon, user_lat)

        # 公尺 → 公里 → 像素
        dx_px = (x_meters / 1000.0) * PIXEL_PER_KM
        dy_px = (y_meters / 1000.0) * PIXEL_PER_KM

        # 映射到圖片像素 (Y 軸反轉，因為圖片左上角是原點)
        px_x = IMAGE_CENTER_PX + dx_px
        px_y = IMAGE_CENTER_PX - dy_px

        return px_x, px_y

    # ─── 圖片標註 ─────────────────────────────────────────
    def mark_location(self, img_bytes, station, user_lat, user_lon):
        """在雷達圖上標註使用者位置 (紅色圓點)，並裁切回傳"""
        center_lat = station["center_lat"]
        center_lon = station["center_lon"]

        # 1. 座標轉像素
        px_x, px_y = self._latlon_to_pixel(center_lat, center_lon, user_lat, user_lon)
        print(f"  [標註] 像素座標: ({px_x:.1f}, {px_y:.1f})")

        # 檢查是否在圖片範圍內
        if not (0 <= px_x < IMAGE_SIZE and 0 <= px_y < IMAGE_SIZE):
            print(f"  [警告] 座標超出雷達圖範圍！")
            return None

        # 2. 畫紅色圓點
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        draw = ImageDraw.Draw(img)

        r = MARKER_RADIUS
        draw.ellipse(
            [px_x - r, px_y - r, px_x + r, px_y + r],
            fill=MARKER_COLOR,
            outline=MARKER_OUTLINE,
            width=MARKER_OUTLINE_WIDTH,
        )

        # 3. 裁切：以使用者位置為中心
        half = CROP_SIZE // 2
        left = max(0, min(IMAGE_SIZE - CROP_SIZE, int(px_x) - half))
        top = max(0, min(IMAGE_SIZE - CROP_SIZE, int(px_y) - half))
        img_cropped = img.crop((left, top, left + CROP_SIZE, top + CROP_SIZE))

        # 4. 轉為 PNG bytes
        output = io.BytesIO()
        img_cropped.convert("RGB").save(output, format="PNG")
        return output.getvalue()

    # ─── 主要入口 ─────────────────────────────────────────
    async def get_marked_radar(self, lat, lon):
        """
        給定使用者座標，自動判斷區域、抓取雷達圖、標註位置並回傳。
        """
        station = self.get_station_for_location(lat, lon)
        dataset_id = station["dataset_id"]
        station_name = station["name"]

        print(f"[雷達] 使用者座標 ({lat}, {lon}) → {station_name} ({dataset_id})")

        img_bytes, img_time_str = await self.fetch_radar_image(dataset_id)
            
        if not img_bytes:
            return None, None

        marked = self.mark_location(img_bytes, station, lat, lon)
        return marked, img_time_str

    async def get_region_radar(self, region_key):
        """
        抓取指定區域的完整雷達圖。
        region_key: 'north', 'central', 'south'
        回傳: (圖片 bytes, 圖片時間字串) 或 (None, None)
        """
        from config.settings import RADAR_STATIONS
        if region_key not in RADAR_STATIONS:
            return None, None
            
        station = RADAR_STATIONS[region_key]
        dataset_id = station["dataset_id"]
        
        img_bytes, img_time_str = await self.fetch_radar_image(dataset_id)
        return img_bytes, img_time_str

