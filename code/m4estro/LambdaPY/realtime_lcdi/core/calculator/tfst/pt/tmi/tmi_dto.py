from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime

import igraph as ig

from core.calculator.tfst.pt.tmi.calculator.tmi_calculation_dto import TMICalculationDTO

@dataclass(frozen=True)
class TMIInputDTO:
    source: ig.Vertex 
    destination: ig.Vertex
    route_geodesic_distance: float
    route_average_time: float
    shipment_estimation_time: datetime 
    departure_time: datetime

@dataclass(frozen=True)
class TMIValueDTO:
    value: float
    computed: bool

@dataclass(frozen=True)
class TMI_DTO(TMICalculationDTO):
    source_index: int
    source_id: int
    source_name: str
    destination_index: int
    destination_id: int
    destination_name: str
    timestamp: datetime

    @staticmethod
    def from_tmi_calculation_dto(tmi_calculation_dto: TMICalculationDTO, 
                                 source_index: int, 
                                 source_id: int, 
                                 source_name: str,
                                 destination_index: int, 
                                 destination_id: int, 
                                 destination_name: str,
                                 timestamp: datetime
                                 ) -> 'TMI_DTO':
        return TMI_DTO(
            value=tmi_calculation_dto.value,
            transportation_mode=tmi_calculation_dto.transportation_mode,
            distance_geodesic_km=tmi_calculation_dto.distance_geodesic_km,
            distance_road_km=tmi_calculation_dto.distance_road_km,
            time_hours=tmi_calculation_dto.time_hours,
            time_road_no_traffic_hours=tmi_calculation_dto.time_road_no_traffic_hours,
            time_road_with_traffic_hours=tmi_calculation_dto.time_road_with_traffic_hours,
            source_index=source_index,
            source_id=source_id,
            source_name=source_name,
            destination_index=destination_index,
            destination_id=destination_id,
            destination_name=destination_name,
            timestamp=timestamp
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "transportation_mode": self.transportation_mode.name,
            "distance_road_km": self.distance_road_km,
            "time_road_no_traffic_hours": self.time_road_no_traffic_hours,
            "time_road_with_traffic_hours": self.time_road_with_traffic_hours,
            "source": {
                "id": self.source_id,
                "name": self.source_name
            },
            "destination": {
                "id": self.destination_id,
                "name": self.destination_name
            },
        }