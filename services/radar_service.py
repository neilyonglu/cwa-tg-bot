import io
from PIL import Image  # noqa: F401 (used via io in get_region_radar)
from config.settings import RADAR_STATIONS, REGION_LAT_BOUNDARIES, RADAR_BACKUP_ORDER
from services.radar_fetch import fetch_radar_image
from services.radar_render import analyze_point_dbz, dbz_to_human_text, mark_location


class RadarService:
    def get_station_for_location(self, lat, lon):
        if lat > REGION_LAT_BOUNDARIES["north"]:
            return RADAR_STATIONS["north"]
        elif lat > REGION_LAT_BOUNDARIES["central"]:
            return RADAR_STATIONS["central"]
        else:
            return RADAR_STATIONS["south"]

    async def get_marked_radar(self, lat, lon):
        station = self.get_station_for_location(lat, lon)
        dataset_id = station["dataset_id"]
        print(f"[雷達] 使用者座標 ({lat}, {lon}) → {station['name']} ({dataset_id})")

        img_bytes, img_time_str = await fetch_radar_image(dataset_id)
        if not img_bytes:
            return None, None, None

        primary_dbz, in_range, is_blind_zone = analyze_point_dbz(
            img_bytes, station, lat, lon
        )
        best_station, best_img_bytes, best_img_time = station, img_bytes, img_time_str
        best_dbz = primary_dbz if primary_dbz is not None else -1

        if in_range and is_blind_zone:
            primary_key = next(
                (k for k, v in RADAR_STATIONS.items() if v["dataset_id"] == dataset_id),
                None,
            )
            for backup_key in RADAR_BACKUP_ORDER.get(primary_key, []):
                backup_station = RADAR_STATIONS[backup_key]
                backup_bytes, backup_time = await fetch_radar_image(
                    backup_station["dataset_id"]
                )
                if not backup_bytes:
                    continue
                backup_dbz, backup_in_range, _ = analyze_point_dbz(
                    backup_bytes, backup_station, lat, lon
                )
                if backup_in_range and backup_dbz is not None and backup_dbz > 0 and backup_dbz > best_dbz:
                    best_station, best_img_bytes, best_img_time, best_dbz = (
                        backup_station,
                        backup_bytes,
                        backup_time,
                        backup_dbz,
                    )

        marked = mark_location(best_img_bytes, best_station, lat, lon)
        if not marked:
            return None, None, None

        return marked, best_img_time, dbz_to_human_text(best_dbz)

    async def get_region_radar(self, region_key):
        if region_key not in RADAR_STATIONS:
            return None, None

        station = RADAR_STATIONS[region_key]
        img_bytes, img_time_str = await fetch_radar_image(station["dataset_id"])
        if not img_bytes:
            return None, None

        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue(), img_time_str
