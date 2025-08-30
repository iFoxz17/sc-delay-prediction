import math
from numbers import Number
from geopy.distance import geodesic, Point

class GeoCalculator:
    def __init__(self):
        pass

    def geodesic_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        assert isinstance(lat1, Number) and -90 <= lat1 <= 90
        assert isinstance(lon1, Number) and -180 <= lon1 <= 180
        assert isinstance(lat2, Number) and -90 <= lat2 <= 90
        assert isinstance(lon2, Number) and -180 <= lon2 <= 180

        return geodesic((lat1, lon1), (lat2, lon2)).kilometers
    
    def bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        assert isinstance(lat1, Number) and -90 <= lat1 <= 90
        assert isinstance(lon1, Number) and -180 <= lon1 <= 180
        assert isinstance(lat2, Number) and -90 <= lat2 <= 90
        assert isinstance(lon2, Number) and -180 <= lon2 <= 180
        
        lat1_rad: float = math.radians(lat1)
        lon1_rad: float = math.radians(lon1)
        lat2_rad: float = math.radians(lat2)
        lon2_rad: float = math.radians(lon2)
    
        delta_lon: float = lon2_rad - lon1_rad
    
        y: float = math.sin(delta_lon) * math.cos(lat2_rad)
        x: float = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
    
        bearing_rad: float = math.atan2(y, x)
        bearing_deg: float = math.degrees(bearing_rad)
    
        bearing_deg: float = (bearing_deg + 360) % 360
        return bearing_deg
    
    def move(self, lat: float, lon: float, distance: float, bearing: float) -> tuple[float, float]:
        assert isinstance(lat, Number) and -90 <= lat <= 90
        assert isinstance(lon, Number) and -180 <= lon <= 180
        assert isinstance(distance, Number) and distance >= 0
        assert isinstance(bearing, Number) and 0 <= bearing < 360
        
        point: Point = geodesic(kilometers=distance).destination(point=Point(lat, lon), bearing=bearing)
        return point.latitude, point.longitude