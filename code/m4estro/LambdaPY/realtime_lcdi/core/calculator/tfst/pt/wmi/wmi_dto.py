from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime

import igraph as ig

from core.calculator.tfst.pt.wmi.calculator.wmi_calculation_dto import WMICalculationDTO

@dataclass(frozen=True)
class WMIInputDTO:
    source: ig.Vertex 
    destination: ig.Vertex
    route_average_time: float
    shipment_estimation_time: datetime 
    departure_time: datetime

@dataclass(frozen=True)
class WMIValueDTO:
    value: float
    computed: bool

@dataclass(frozen=True)
class WMI_DTO(WMICalculationDTO):
    source_index: int
    source_id: int
    source_name: str
    destination_index: int
    destination_id: int
    destination_name: str
    timestamp: datetime
    n_interpolation_points: int
    step_distance_km: float


    @staticmethod
    def from_wmi_calculation_dto(wmi_calculation_dto: WMICalculationDTO, 
                                 source_index: int, 
                                 source_id: int, 
                                 source_name: str,
                                 destination_index: int, 
                                 destination_id: int, 
                                 destination_name: str,
                                 timestamp: datetime,
                                 n_interpolation_points: int,
                                 step_distance_km: float
                                 ) -> 'WMI_DTO':
        return WMI_DTO(
            value=wmi_calculation_dto.value,
            weather_code=wmi_calculation_dto.weather_code,
            weather_description=wmi_calculation_dto.weather_description,
            temperature_celsius=wmi_calculation_dto.temperature_celsius,
            by=wmi_calculation_dto.by,
            source_index=source_index,
            source_id=source_id,
            source_name=source_name,
            destination_index=destination_index,
            destination_id=destination_id,
            destination_name=destination_name,
            timestamp=timestamp,
            n_interpolation_points=n_interpolation_points,
            step_distance_km=step_distance_km
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "weather_code": self.weather_code,
            "weather_description": self.weather_description,
            "temperature_celsius": self.temperature_celsius,
            "by": self.by.value,
            "source": {
                "id": self.source_id,
                "name": self.source_name,
                "index": self.source_index
            },
            "destination": {
                "id": self.destination_id,
                "name": self.destination_name,
                "index": self.destination_index
            },
            "timestamp": self.timestamp.isoformat(),
            "n_interpolation_points": self.n_interpolation_points,
            "step_distance_km": self.step_distance_km
        }