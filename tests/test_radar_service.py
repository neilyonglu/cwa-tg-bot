from services.radar_service import RadarService
from config.settings import RADAR_STATIONS, REGION_LAT_BOUNDARIES


class TestGetStationForLocation:
    def setup_method(self):
        self.service = RadarService()

    def test_north_taiwan(self):
        station = self.service.get_station_for_location(25.0, 121.5)
        assert station == RADAR_STATIONS["north"]

    def test_central_taiwan(self):
        station = self.service.get_station_for_location(24.0, 120.7)
        assert station == RADAR_STATIONS["central"]

    def test_south_taiwan(self):
        station = self.service.get_station_for_location(22.5, 120.3)
        assert station == RADAR_STATIONS["south"]

    def test_boundary_north(self):
        lat = REGION_LAT_BOUNDARIES["north"]
        station_above = self.service.get_station_for_location(lat + 0.01, 121.0)
        station_at = self.service.get_station_for_location(lat, 121.0)
        assert station_above == RADAR_STATIONS["north"]
        assert station_at == RADAR_STATIONS["central"]

    def test_boundary_central(self):
        lat = REGION_LAT_BOUNDARIES["central"]
        station_above = self.service.get_station_for_location(lat + 0.01, 121.0)
        station_at = self.service.get_station_for_location(lat, 121.0)
        assert station_above == RADAR_STATIONS["central"]
        assert station_at == RADAR_STATIONS["south"]
