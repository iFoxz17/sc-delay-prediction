from typing import TYPE_CHECKING
from model.tmi import TransportationMode

from core.calculator.tfst.pt.tmi.calculator.tmi_calculation_dto import TMICalculationDTO

if TYPE_CHECKING:
    from core.query_handler.params.params_result import TMISpeedParameters, TMIDistanceParameters
    from core.calculator.tfst.pt.tmi.calculator.tmi_calculation_input_dto import TMICalculationInputDTO

from logger import get_logger
logger = get_logger(__name__)

class TMICalculator:
    def __init__(self, tmi_speed_params: 'TMISpeedParameters', tmi_distance_params: 'TMIDistanceParameters') -> None:
        self.tmi_speed_params: 'TMISpeedParameters' = tmi_speed_params
        self.tmi_distance_params: 'TMIDistanceParameters' = tmi_distance_params

    def get_transportation_mode(self, distance_km: float, time_hours: float) -> TransportationMode:
        speed_params: 'TMISpeedParameters' = self.tmi_speed_params
        distance_params: 'TMIDistanceParameters' = self.tmi_distance_params
        
        speed_km_h: float = distance_km / time_hours
        
        if speed_params.air_min_speed_km_h <= speed_km_h <= speed_params.air_max_speed_km_h and distance_params.air_min_distance_km <= distance_km <= distance_params.air_max_distance_km:
            logger.debug(f"Calculated speed {speed_km_h} km/h and distance {distance_km} km indicate transportation mode: AIR")
            return TransportationMode.AIR

        if speed_params.sea_min_speed_km_h <= speed_km_h <= speed_params.sea_max_speed_km_h and distance_params.sea_min_distance_km <= distance_km <= distance_params.sea_max_distance_km:
            logger.debug(f"Calculated speed {speed_km_h} km/h and distance {distance_km} km indicate transportation mode: SEA")
            return TransportationMode.SEA
        
        if speed_params.rail_min_speed_km_h <= speed_km_h <= speed_params.rail_max_speed_km_h and distance_params.rail_min_distance_km <= distance_km <= distance_params.rail_max_distance_km:
            logger.debug(f"Calculated speed {speed_km_h} km/h and distance {distance_km} km indicate transportation mode: RAIL")
            return TransportationMode.RAIL
        
        if speed_params.road_min_speed_km_h <= speed_km_h <= speed_params.road_max_speed_km_h and distance_params.road_min_distance_km <= distance_km <= distance_params.road_max_distance_km:
            logger.debug(f"Calculated speed {speed_km_h} km/h and distance {distance_km} km indicate transportation mode: ROAD")
            return TransportationMode.ROAD
        
        return TransportationMode.UNKNOWN
    
    def _empty_tmi_dto(self, tmi_input: 'TMICalculationInputDTO', transportation_mode: TransportationMode) -> TMICalculationDTO:
        return TMICalculationDTO(
            value=0.0,
            transportation_mode=transportation_mode,
            distance_geodesic_km=tmi_input.distance_geodesic_km,
            distance_road_km=tmi_input.distance_road_km,
            time_hours=tmi_input.time_hours,
            time_road_no_traffic_hours=0.0,
            time_road_with_traffic_hours=0.0
        )
    
    def _calculate_tmi_value(self, tmi_input: 'TMICalculationInputDTO', transportation_mode: TransportationMode) -> TMICalculationDTO:
        time_road_no_traffic_hours: float = tmi_input.time_road_no_traffic_hours
        if time_road_no_traffic_hours <= 0:
            logger.warning(f"Time without traffic is zero or negative: {time_road_no_traffic_hours}. Cannot calculate TMI.")
            return self._empty_tmi_dto(tmi_input, transportation_mode)
        
        time_road_with_traffic_hours: float = tmi_input.time_road_with_traffic_hours
        if time_road_with_traffic_hours < time_road_no_traffic_hours:
            logger.warning(f"Time with traffic {time_road_with_traffic_hours} is less than time without traffic {time_road_no_traffic_hours}. Cannot calculate TMI.")
            return self._empty_tmi_dto(tmi_input, transportation_mode)

        tmi: float = (tmi_input.time_road_with_traffic_hours - tmi_input.time_road_no_traffic_hours) / tmi_input.time_road_no_traffic_hours
        logger.debug(f"TMI calculated succesfully: {tmi}")

        return TMICalculationDTO(
            value=tmi,
            transportation_mode=transportation_mode,
            distance_geodesic_km=tmi_input.distance_geodesic_km,
            distance_road_km=tmi_input.distance_road_km,
            time_hours=tmi_input.time_hours,
            time_road_no_traffic_hours=time_road_no_traffic_hours,
            time_road_with_traffic_hours=time_road_with_traffic_hours
        )

    def calculate(self, tmi_input: 'TMICalculationInputDTO') -> TMICalculationDTO:
        transportation_mode: TransportationMode = self.get_transportation_mode(
            distance_km=tmi_input.distance_geodesic_km,
            time_hours=tmi_input.time_hours
        )

        if transportation_mode != TransportationMode.RAIL and transportation_mode != TransportationMode.ROAD:
            return self._empty_tmi_dto(tmi_input, transportation_mode)
        
        return self._calculate_tmi_value(tmi_input, transportation_mode)