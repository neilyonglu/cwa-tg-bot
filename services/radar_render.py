import io
from PIL import Image, ImageDraw
from pyproj import Transformer
from config.settings import (
    IMAGE_SIZE,
    IMAGE_CENTER_PX,
    PIXEL_PER_KM,
    MARKER_RADIUS,
    MARKER_COLOR,
    MARKER_OUTLINE,
    MARKER_OUTLINE_WIDTH,
    CROP_SIZE,
    DBZ_COLOR_SCALE,
)

_dbz_color_to_value: dict = {color: dbz for dbz, color in enumerate(DBZ_COLOR_SCALE)}


def latlon_to_pixel(center_lat, center_lon, user_lat, user_lon):
    transformer = Transformer.from_crs(
        "EPSG:4326",
        f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} +datum=WGS84",
        always_xy=True,
    )
    x_meters, y_meters = transformer.transform(user_lon, user_lat)
    px_x = IMAGE_CENTER_PX + (x_meters / 1000.0) * PIXEL_PER_KM
    px_y = IMAGE_CENTER_PX - (y_meters / 1000.0) * PIXEL_PER_KM
    return px_x, px_y


def match_dbz_from_color(rgb: tuple) -> int | None:
    if rgb in _dbz_color_to_value:
        return _dbz_color_to_value[rgb]

    nearest_dbz, nearest_dist = None, None
    r, g, b = rgb
    for dbz, (cr, cg, cb) in enumerate(DBZ_COLOR_SCALE):
        dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if nearest_dist is None or dist < nearest_dist:
            nearest_dist, nearest_dbz = dist, dbz

    if nearest_dist is not None and nearest_dist <= 100:
        return nearest_dbz
    return None


def analyze_point_dbz(
    img_bytes: bytes, station: dict, user_lat: float, user_lon: float
):
    px_x, px_y = latlon_to_pixel(
        station["center_lat"], station["center_lon"], user_lat, user_lon
    )
    if not (0 <= px_x < IMAGE_SIZE and 0 <= px_y < IMAGE_SIZE):
        return None, False, False

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    x = max(0, min(IMAGE_SIZE - 1, int(round(px_x))))
    y = max(0, min(IMAGE_SIZE - 1, int(round(px_y))))
    dbz = match_dbz_from_color(img.getpixel((x, y)))
    return dbz, True, dbz == 0


def dbz_to_human_text(dbz) -> str:
    if dbz is None or dbz <= 0:
        return "☀️ 目前無明顯降雨"
    if dbz < 15:
        return "☁️ 雲系籠罩，注意微雨"
    if dbz < 30:
        return "🌧️ 正在下雨（一般雨勢）"
    if dbz < 45:
        return "⛈️ 雨勢明顯，外出請注意安全"
    return "⚠️ 強降雨警告，請遠離低窪地區"


def mark_location(
    img_bytes: bytes, station: dict, user_lat: float, user_lon: float
) -> bytes | None:
    px_x, px_y = latlon_to_pixel(
        station["center_lat"], station["center_lon"], user_lat, user_lon
    )
    print(f"  [標註] 像素座標: ({px_x:.1f}, {px_y:.1f})")
    if not (0 <= px_x < IMAGE_SIZE and 0 <= px_y < IMAGE_SIZE):
        print("  [警告] 座標超出雷達圖範圍！")
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
