from dataclasses import dataclass

@dataclass(frozen=True)
class TMICalculationInputDTO:
    distance_geodesic_km: float
    distance_road_km: float
    
    time_hours: float
    time_road_no_traffic_hours: float
    time_road_with_traffic_hours: float