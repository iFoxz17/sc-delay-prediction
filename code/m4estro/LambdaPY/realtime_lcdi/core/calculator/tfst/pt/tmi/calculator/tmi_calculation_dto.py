from dataclasses import dataclass
from model.tmi import TransportationMode

@dataclass(frozen=True)
class TMICalculationDTO:
    value: float
    transportation_mode: TransportationMode

    distance_geodesic_km: float
    distance_road_km: float

    time_hours: float
    time_road_no_traffic_hours: float
    time_road_with_traffic_hours: float