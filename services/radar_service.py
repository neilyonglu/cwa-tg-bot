import requests
import time
import io
import asyncio
from datetime import datetime
from PIL import Image, ImageDraw
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
    DBZ_COLOR_SCALE,
    RADAR_BACKUP_ORDER,
)


class RadarService:
    _cache = {}  # {dataset_id: (image_bytes, timestamp, img_time_str)} — 所有實例共用

    def __init__(self):
        self._dbz_color_to_value = {color: dbz for dbz, color in enumerate(DBZ_COLOR_SCALE)}

    # ─── 區域判斷 ─────────────────────────────────────────
    def get_station_for_location(self, lat, lon):
        if lat > REGION_LAT_BOUNDARIES["north"]:
            return RADAR_STATIONS["north"]
        elif lat > REGION_LAT_BOUNDARIES["central"]:
            return RADAR_STATIONS["central"]
        else:
            return RADAR_STATIONS["south"]

    # ─── 圖資取得 (S3) ────────────────────────────────────
    async def fetch_radar_image(self, dataset_id, force_refresh=False):
        if not force_refresh and dataset_id in self._cache:
            img_bytes, timestamp, img_time_str = self._cache[dataset_id]
            age = time.time() - timestamp
            if age < CACHE_TTL:
                print(f"  [快取命中] {dataset_id} (已快取 {age:.0f} 秒)")
                return img_bytes, img_time_str

        try:
            s3_img_url = f"{CWA_S3_BASE_URL}/{dataset_id}.png"
            s3_json_url = f"{CWA_S3_BASE_URL}/{dataset_id}.json"

            print(f"  [S3] 下載 {s3_img_url}")
            loop = asyncio.get_event_loop()
            img_response = await loop.run_in_executor(None, requests.get, s3_img_url)
            img_response.raise_for_status()

            img_bytes = img_response.content

            # 另外抓 JSON 取得 CWA 官方的圖片產生時間
            img_time_str = "未知時間"
            try:
                json_response = await loop.run_in_executor(None, requests.get, s3_json_url)
                if json_response.status_code == 200:
                    data = json_response.json()
                    dt_str = data["cwaopendata"]["dataset"]["DateTime"]
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
        # AEQD：從中心點到任意方向的距離保真，與雷達掃描原理一致
        transformer = Transformer.from_crs(
            "EPSG:4326",  # WGS84
            f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} +datum=WGS84",
            always_xy=True,
        )

        x_meters, y_meters = transformer.transform(user_lon, user_lat)

        # 公尺 → 公里 → 像素
        dx_px = (x_meters / 1000.0) * PIXEL_PER_KM
        dy_px = (y_meters / 1000.0) * PIXEL_PER_KM

        # Y 軸反轉：圖片座標系左上角為原點
        px_x = IMAGE_CENTER_PX + dx_px
        px_y = IMAGE_CENTER_PX - dy_px

        return px_x, px_y

    def _match_dbz_from_color(self, rgb):
        if rgb in self._dbz_color_to_value:
            return self._dbz_color_to_value[rgb]

        nearest_dbz = None
        nearest_dist = None
        r, g, b = rgb
        for dbz, color in enumerate(DBZ_COLOR_SCALE):
            cr, cg, cb = color
            dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if nearest_dist is None or dist < nearest_dist:
                nearest_dist = dist
                nearest_dbz = dbz

        # PNG 色碼理論上應精確，保守設容差 100 避免把背景色誤判為雨
        if nearest_dist is not None and nearest_dist <= 100:
            return nearest_dbz
        return None

    def _analyze_point_dbz(self, img_bytes, station, user_lat, user_lon):
        px_x, px_y = self._latlon_to_pixel(
            station["center_lat"],
            station["center_lon"],
            user_lat,
            user_lon,
        )

        in_range = 0 <= px_x < IMAGE_SIZE and 0 <= px_y < IMAGE_SIZE
        if not in_range:
            return None, False, False

        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        x = max(0, min(IMAGE_SIZE - 1, int(round(px_x))))
        y = max(0, min(IMAGE_SIZE - 1, int(round(px_y))))
        pixel = img.getpixel((x, y))
        dbz = self._match_dbz_from_color(pixel)

        # dbz == 0 代表該站對此點無回波，可能是單站盲區
        is_blind_zone = dbz == 0
        return dbz, True, is_blind_zone

    def _dbz_to_human_text(self, dbz):
        if dbz is None or dbz <= 0:
            return "☀️ 目前無明顯降雨"
        if 1 <= dbz < 15:
            return "☁️ 雲系籠罩，注意微雨"
        if 15 <= dbz < 30:
            return "🌧️ 正在下雨（一般雨勢）"
        if 30 <= dbz < 45:
            return "⛈️ 雨勢明顯，外出請注意安全"
        return "⚠️ 強降雨警告，請遠離低窪地區"

    # ─── 圖片標註 ─────────────────────────────────────────
    def mark_location(self, img_bytes, station, user_lat, user_lon):
        px_x, px_y = self._latlon_to_pixel(
            station["center_lat"], station["center_lon"], user_lat, user_lon
        )
        print(f"  [標註] 像素座標: ({px_x:.1f}, {px_y:.1f})")

        if not (0 <= px_x < IMAGE_SIZE and 0 <= px_y < IMAGE_SIZE):
            print(f"  [警告] 座標超出雷達圖範圍！")
            return None

        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        draw = ImageDraw.Draw(img)
        r = MARKER_RADIUS
        draw.ellipse(
            [px_x - r, px_y - r, px_x + r, px_y + r],
            fill=MARKER_COLOR,
            outline=MARKER_OUTLINE,
            width=MARKER_OUTLINE_WIDTH,
        )

        half = CROP_SIZE // 2
        left = max(0, min(IMAGE_SIZE - CROP_SIZE, int(px_x) - half))
        top = max(0, min(IMAGE_SIZE - CROP_SIZE, int(px_y) - half))
        img_cropped = img.crop((left, top, left + CROP_SIZE, top + CROP_SIZE))

        output = io.BytesIO()
        img_cropped.convert("RGB").save(output, format="PNG")
        return output.getvalue()

    # ─── 主要入口 ─────────────────────────────────────────
    async def get_marked_radar(self, lat, lon):
        station = self.get_station_for_location(lat, lon)
        dataset_id = station["dataset_id"]
        station_name = station["name"]

        print(f"[雷達] 使用者座標 ({lat}, {lon}) → {station_name} ({dataset_id})")

        img_bytes, img_time_str = await self.fetch_radar_image(dataset_id)
        if not img_bytes:
            return None, None, None

        primary_dbz, in_range, is_blind_zone = self._analyze_point_dbz(img_bytes, station, lat, lon)
        best_station = station
        best_img_bytes = img_bytes
        best_img_time = img_time_str
        best_dbz = primary_dbz if primary_dbz is not None else -1

        if in_range and is_blind_zone:
            primary_region_key = next(
                (key for key, info in RADAR_STATIONS.items() if info["dataset_id"] == dataset_id),
                None,
            )
            backup_keys = RADAR_BACKUP_ORDER.get(primary_region_key, [])
            for backup_key in backup_keys:
                backup_station = RADAR_STATIONS[backup_key]
                backup_img_bytes, backup_img_time = await self.fetch_radar_image(backup_station["dataset_id"])
                if not backup_img_bytes:
                    continue
                backup_dbz, backup_in_range, _ = self._analyze_point_dbz(
                    backup_img_bytes, backup_station, lat, lon
                )
                if backup_in_range and backup_dbz is not None and backup_dbz > best_dbz:
                    best_station = backup_station
                    best_img_bytes = backup_img_bytes
                    best_img_time = backup_img_time
                    best_dbz = backup_dbz

        marked = self.mark_location(best_img_bytes, best_station, lat, lon)
        if not marked:
            return None, None, None

        return marked, best_img_time, self._dbz_to_human_text(best_dbz)

    async def get_region_radar(self, region_key):
        if region_key not in RADAR_STATIONS:
            return None, None

        station = RADAR_STATIONS[region_key]
        img_bytes, img_time_str = await self.fetch_radar_image(station["dataset_id"])
        if not img_bytes:
            return None, None

        # 重新編碼，避免 Telegram API 拒絕原始 S3 PNG 的格式
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        output = io.BytesIO()
        img.save(output, format="PNG")

        return output.getvalue(), img_time_str
