from typing import TYPE_CHECKING, List
from datetime import datetime, timedelta

import igraph as ig

from graph_config import V_ID_ATTR, LATITUDE_ATTR, LONGITUDE_ATTR

from service.lambda_client.traffic_service_lambda_client import TrafficRequest

from model.tmi import TransportationMode

from core.calculator.tfst.pt.tmi.calculator.tmi_calculation_input_dto import TMICalculationInputDTO
from core.calculator.tfst.pt.tmi.tmi_dto import TMI_DTO, TMIValueDTO, TMIInputDTO

if TYPE_CHECKING:
    from service.lambda_client.traffic_service_lambda_client import TrafficServiceLambdaClient, TrafficResult
    from core.calculator.tfst.pt.tmi.calculator.tmi_calculation_dto import TMICalculationDTO
    from core.calculator.tfst.pt.tmi.calculator.tmi_calculator import TMICalculator

from logger import get_logger
logger = get_logger(__name__)

class TMIManager:
    def __init__(self, 
                 lambda_client: 'TrafficServiceLambdaClient',
                 calculator: 'TMICalculator',
                 use_traffic_service: bool,
                 max_timedelta: float,
                 ) -> None:
        self.lambda_client: 'TrafficServiceLambdaClient' = lambda_client
        self.calculator: 'TMICalculator' = calculator

        self.use_traffic_service: bool = use_traffic_service
        self.max_timedelta: float = max_timedelta

        self.tmi_data: List['TMI_DTO'] = []

    def initialize(self) -> None:
        logger.debug("Initializing TMIManager data repository.")
        self.tmi_data: List['TMI_DTO'] = []

    def _meets_save_conditions(self, tmi: TMI_DTO) -> bool:
        return tmi.transportation_mode == TransportationMode.ROAD or tmi.transportation_mode == TransportationMode.RAIL

    def calculate_tmi(self, tmi_input: TMIInputDTO) -> TMIValueDTO:
        if not self.use_traffic_service:
            logger.debug("Traffic service not enabled: skipping TMI calculation.")
            return TMIValueDTO(value=0.0, computed=False)

        source: ig.Vertex = tmi_input.source
        destination: ig.Vertex = tmi_input.destination
        route_geodesic_distance: float = tmi_input.route_geodesic_distance
        route_average_time: float = tmi_input.route_average_time
        shipment_estimation_time: datetime = tmi_input.shipment_estimation_time
        departure_time: datetime = tmi_input.departure_time

        if departure_time - shipment_estimation_time > timedelta(hours=self.max_timedelta):
            logger.debug(f"Departure time {departure_time} exceeds max timedelta from estimation time {shipment_estimation_time}. Skipping TMI calculation.")
            return TMIValueDTO(value=0.0, computed=False)
        
        logger.debug(f"Calculating TMI for source {source[V_ID_ATTR]} ({source['name']}) and destination {destination[V_ID_ATTR]} ({destination['name']}) at {departure_time.isoformat()}")
        request: TrafficRequest = TrafficRequest(
            source_latitude=source[LATITUDE_ATTR],
            source_longitude=source[LONGITUDE_ATTR],
            destination_latitude=destination[LATITUDE_ATTR],
            destination_longitude=destination[LONGITUDE_ATTR],
            departure_time=departure_time,
            transportation_mode=TransportationMode.ROAD
        )

        result: 'TrafficResult' = self.lambda_client.get_traffic_data(request)
        logger.debug(f"Received traffic data: {result}")

        if result.error:
            logger.debug(f"Error retrieving traffic data for source {source[V_ID_ATTR]} and destination {destination[V_ID_ATTR]}. Returning empty TMI value.")
            return TMIValueDTO(value=0.0, computed=False)

        tmi_calculation_input: TMICalculationInputDTO = TMICalculationInputDTO(
            distance_geodesic_km=route_geodesic_distance,
            distance_road_km=result.distance_km,
            time_hours=route_average_time,
            time_road_no_traffic_hours=result.no_traffic_travel_time_hours,
            time_road_with_traffic_hours=result.travel_time_hours,
        )

        tmi: 'TMICalculationDTO' = self.calculator.calculate(tmi_calculation_input)
        logger.debug(f"Calculated TMI: {tmi}")

        tmi_dto: TMI_DTO = TMI_DTO.from_tmi_calculation_dto(
            tmi_calculation_dto=tmi,
            source_index=source.index,
            source_id=source[V_ID_ATTR],
            source_name=source['name'],
            destination_index=destination.index,
            destination_id=destination[V_ID_ATTR],
            destination_name=destination['name'],
            timestamp=departure_time
        )

        if self._meets_save_conditions(tmi_dto):
            self.tmi_data.append(tmi_dto)
            logger.debug(f"Stored TMI DTO: {tmi_dto}")
        else:
            logger.debug(f"Avoided storing TMI DTO")

        return TMIValueDTO(value=tmi.value, computed=True)