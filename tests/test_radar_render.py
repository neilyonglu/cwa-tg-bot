import pytest
from services.radar_render import dbz_to_human_text, match_dbz_from_color, latlon_to_pixel
from config.settings import DBZ_COLOR_SCALE, IMAGE_CENTER_PX


class TestDbzToHumanText:
    def test_none_returns_no_rain(self):
        assert "無明顯降雨" in dbz_to_human_text(None)

    def test_zero_returns_no_rain(self):
        assert "無明顯降雨" in dbz_to_human_text(0)

    def test_negative_returns_no_rain(self):
        assert "無明顯降雨" in dbz_to_human_text(-1)

    def test_light_rain(self):
        assert "微雨" in dbz_to_human_text(10)

    def test_moderate_rain(self):
        assert "一般雨勢" in dbz_to_human_text(20)

    def test_heavy_rain(self):
        assert "明顯" in dbz_to_human_text(35)

    def test_extreme_rain(self):
        assert "強降雨" in dbz_to_human_text(50)


class TestMatchDbzFromColor:
    def test_exact_color_match(self):
        color = DBZ_COLOR_SCALE[15]
        assert match_dbz_from_color(color) == 15

    def test_first_color(self):
        assert match_dbz_from_color(DBZ_COLOR_SCALE[0]) == 0

    def test_last_color(self):
        last = len(DBZ_COLOR_SCALE) - 1
        assert match_dbz_from_color(DBZ_COLOR_SCALE[last]) == last

    def test_no_match_returns_none(self):
        assert match_dbz_from_color((128, 128, 128)) is None

    def test_near_color_within_threshold(self):
        r, g, b = DBZ_COLOR_SCALE[15]
        result = match_dbz_from_color((r + 1, g + 1, b + 1))
        assert result == 15

    def test_near_color_outside_threshold(self):
        result = match_dbz_from_color((100, 100, 100))
        assert result is None


class TestLatLonToPixel:
    CENTER_LAT = 25.000
    CENTER_LON = 121.400

    def test_center_maps_to_image_center(self):
        px_x, px_y = latlon_to_pixel(self.CENTER_LAT, self.CENTER_LON, self.CENTER_LAT, self.CENTER_LON)
        assert abs(px_x - IMAGE_CENTER_PX) < 1
        assert abs(px_y - IMAGE_CENTER_PX) < 1

    def test_north_of_center_gives_smaller_y(self):
        _, py_center = latlon_to_pixel(self.CENTER_LAT, self.CENTER_LON, self.CENTER_LAT, self.CENTER_LON)
        _, py_north = latlon_to_pixel(self.CENTER_LAT, self.CENTER_LON, self.CENTER_LAT + 0.1, self.CENTER_LON)
        assert py_north < py_center

    def test_east_of_center_gives_larger_x(self):
        px_center, _ = latlon_to_pixel(self.CENTER_LAT, self.CENTER_LON, self.CENTER_LAT, self.CENTER_LON)
        px_east, _ = latlon_to_pixel(self.CENTER_LAT, self.CENTER_LON, self.CENTER_LAT, self.CENTER_LON + 0.1)
        assert px_east > px_center
