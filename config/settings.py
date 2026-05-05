# config/settings.py
"""
集中管理雷達站設定與常數
"""

# 雷達站定義 (資料集代號, 站名, 中心經度, 中心緯度)
RADAR_STATIONS = {
    "north": {
        "dataset_id": "O-A0084-001",
        "name": "北部(樹林)",
        "center_lon": 121.400,
        "center_lat": 25.000,
    },
    "central": {
        "dataset_id": "O-A0084-002",
        "name": "中部(南屯)",
        "center_lon": 120.579,
        "center_lat": 24.144,
    },
    "south": {
        "dataset_id": "O-A0084-003",
        "name": "南部(林園)",
        "center_lon": 120.379,
        "center_lat": 22.526,
    },
}

# 區域判斷：依緯度分界
REGION_LAT_BOUNDARIES = {
    "north": 24.6,   # lat > 24.6 → 北部
    "central": 23.3, # 23.3 < lat <= 24.6 → 中部
    # lat <= 23.3 → 南部
}

# 圖片相關常數
IMAGE_SIZE = 3600           # 雷達圖為 3600 x 3600 px
IMAGE_CENTER_PX = 1800      # 圖片中心像素 (3600 / 2)
PIXEL_PER_KM = 11.96        # 每公里對應的像素數

# 快取時間 (秒)
CACHE_TTL = 600  # 10 分鐘

# CWA S3 圖資來源
CWA_S3_BASE_URL = "https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation"

# 標記樣式
MARKER_RADIUS = 6      # 紅色圓點半徑 (px)
MARKER_COLOR = "red"
MARKER_OUTLINE = "white"
MARKER_OUTLINE_WIDTH = 1

# 裁切大小 (以使用者位置為中心)
CROP_SIZE = 450
