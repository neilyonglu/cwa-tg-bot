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
    _history = {} # {dataset_id: [(dt_obj, img_bytes, img_time_str), ...]} 存放歷史紀錄，最多 1 小時

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
    def fetch_radar_image(self, dataset_id, force_refresh=False):
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
            img_response = requests.get(s3_img_url)
            img_response.raise_for_status()

            img_bytes = img_response.content
            
            # 解析圖片產生時間 (從 S3 上的 JSON 取得官方時間)
            img_time_str = "未知時間"
            try:
                json_response = requests.get(s3_json_url)
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
    def get_marked_radar(self, lat, lon):
        """
        給定使用者座標，自動判斷區域、抓取雷達圖、標註位置並回傳。
        回傳: (圖片 bytes, 圖片時間字串) 或 (None, None)
        """
        station = self.get_station_for_location(lat, lon)
        dataset_id = station["dataset_id"]
        station_name = station["name"]

        print(f"[雷達] 使用者座標 ({lat}, {lon}) → {station_name} ({dataset_id})")

        img_bytes, img_time_str = self.fetch_radar_image(dataset_id)
        if not img_bytes:
            return None, None

        marked = self.mark_location(img_bytes, station, lat, lon)
        return marked, img_time_str

    def get_region_radar(self, region_key):
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
        
        img_bytes, img_time_str = self.fetch_radar_image(dataset_id)
        return img_bytes, img_time_str

    # ─── 背景輪詢與 GIF 產生 ──────────────────────────────
    async def _fetch_metadata(self, dataset_id):
        """只抓取 JSON 判斷是否有新資料，節省頻寬"""
        s3_json_url = f"{CWA_S3_BASE_URL}/{dataset_id}.json"
        try:
            # 使用 loop.run_in_executor 來避免 requests 阻塞 async loop
            loop = asyncio.get_event_loop()
            json_response = await loop.run_in_executor(None, requests.get, s3_json_url)
            if json_response.status_code == 200:
                data = json_response.json()
                dt_str = data["cwaopendata"]["dataset"]["DateTime"]
                return datetime.fromisoformat(dt_str)
        except Exception as e:
            print(f"  [Meta抓取失敗] {e}")
        return None

    @classmethod
    async def start_background_task(cls):
        """背景輪詢任務，每隔一段時間檢查是否有新圖檔"""
        from config.settings import RADAR_STATIONS
        print("--- 啟動雷達圖背景輪詢服務 ---")
        
        # 初始化 _history
        for region_key, station in RADAR_STATIONS.items():
            dataset_id = station["dataset_id"]
            if dataset_id not in cls._history:
                cls._history[dataset_id] = []

        while True:
            any_new = False
            for region_key, station in RADAR_STATIONS.items():
                dataset_id = station["dataset_id"]
                
                # 先抓取 JSON 判斷時間
                latest_dt = await cls()._fetch_metadata(dataset_id)
                if not latest_dt:
                    continue
                
                history_list = cls._history[dataset_id]
                
                # 判斷是否需要抓取新圖
                is_new = True
                if history_list and history_list[-1][0] == latest_dt:
                    is_new = False
                
                if is_new:
                    any_new = True
                    print(f"  [背景] 發現新圖 {dataset_id} 時間: {latest_dt.strftime('%H:%M')}")
                    # 強制更新，避免被快取擋住
                    img_bytes, img_time_str = cls().fetch_radar_image(dataset_id, force_refresh=True)
                    if img_bytes:
                        # 存入歷史
                        history_list.append((latest_dt, img_bytes, img_time_str))
                        
                        # [除錯用] 將圖片存下來供檢查
                        import os
                        os.makedirs("output/debug_frames", exist_ok=True)
                        debug_filename = f"output/debug_frames/{dataset_id}_{latest_dt.strftime('%H%M')}.png"
                        with open(debug_filename, "wb") as f:
                            f.write(img_bytes)
                        print(f"  [背景] 已儲存除錯圖片: {debug_filename}")
                        
                        # 保持最多 1 小時 (大約 6 張)
                        # 為保險起見，我們用時間過濾，踢掉超過 60 分鐘的
                        cutoff_time = latest_dt - timedelta(minutes=65)
                        cls._history[dataset_id] = [item for item in history_list if item[0] > cutoff_time]
                        print(f"  [背景] {dataset_id} 歷史數量: {len(cls._history[dataset_id])}")
            
            # 決定等待時間
            # 如果剛才有抓到任何新圖片，我們就等 1.5 分鐘 (90 秒)
            # 因為官方大約 1分40秒 會更新一次
            if any_new:
                await asyncio.sleep(90)
            else:
                await asyncio.sleep(10)

    def generate_gif(self, region_key, minutes):
        """根據指定的過去時間 (分鐘)，產生動態 GIF"""
        from config.settings import RADAR_STATIONS
        if region_key not in RADAR_STATIONS:
            return None
            
        dataset_id = RADAR_STATIONS[region_key]["dataset_id"]
        history_list = self.__class__._history.get(dataset_id, [])
        
        if not history_list:
            return None
            
        # 過濾出需要的時間範圍
        latest_dt = history_list[-1][0]
        cutoff_dt = latest_dt - timedelta(minutes=minutes + 1)
        
        frames = []
        for item in history_list:
            dt_obj, img_bytes, img_time_str = item
            if dt_obj >= cutoff_dt:
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                # 恢復縮小為 800x800 以利 Telegram 傳輸，並使用 NEAREST 保留真實色碼
                img.thumbnail((800, 800), Image.Resampling.NEAREST)
                frames.append(img)
                
        if len(frames) == 0:
            return None
            
        if len(frames) == 1:
            # 只有一張圖，直接回傳那張就好 (不需要 GIF)
            output = io.BytesIO()
            frames[0].save(output, format="PNG")
            return output.getvalue(), False # False 代表不是 GIF
            
        # 多張圖片，合成 GIF
        output = io.BytesIO()
        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=500, # 每張顯示 0.5 秒
            loop=0, # 0 代表無限迴圈
            optimize=True # 啟用檔案最佳化
        )
        return output.getvalue(), True # True 代表是 GIF

