from typing import TYPE_CHECKING, List, Set, Optional, Tuple
from datetime import datetime, timedelta
import math

import igraph as ig

from geo_calculator import GeoCalculator
from graph_config import V_ID_ATTR, LATITUDE_ATTR, LONGITUDE_ATTR

from service.lambda_client.weather_service_lambda_client import WeatherRequest

from core.query_handler.params.params_result import WMIParams

from core.calculator.tfst.pt.wmi.calculator.wmi_calculation_input_dto import WMICalculationInputDTO
from core.calculator.tfst.pt.wmi.wmi_dto import WMI_DTO, WMIValueDTO, WMIInputDTO

if TYPE_CHECKING:
    from service.lambda_client.weather_service_lambda_client import WeatherServiceLambdaClient, WeatherResult
    from core.calculator.tfst.pt.wmi.calculator.wmi_calculator import WMICalculator
    from core.calculator.tfst.pt.wmi.calculator.wmi_calculation_dto import WMICalculationDTO

from logger import get_logger
logger = get_logger(__name__)

class WMIManager:
    def __init__(self, 
                 lambda_client: 'WeatherServiceLambdaClient',
                 calculator: 'WMICalculator',
                 params: WMIParams,
                 maybe_geo_calculator: Optional[GeoCalculator] = None
                 ) -> None:
        self.lambda_client: 'WeatherServiceLambdaClient' = lambda_client
        self.calculator: 'WMICalculator' = calculator

        self.use_traffic_service: bool = params.use_weather_service
        self.max_timedelta: float = params.weather_max_timedelta
        
        self.step_km: float = params.step_distance_km
        self.max_points: int = params.max_points

        self.geo_calculator: GeoCalculator = maybe_geo_calculator or GeoCalculator()
        self.wmi_data: List['WMI_DTO'] = []

    def initialize(self) -> None:
        logger.debug("Initializing WMIManager data repository.")
        self.wmi_data: List['WMI_DTO'] = []

    def _meets_save_conditions(self, wmi: WMI_DTO) -> bool:
        return True

    def _interpolate_route(self, s_lat: float, s_lon: float, d_lat: float, d_lon: float) -> Tuple[List[Tuple[float, float]], float, float]:
        geo: GeoCalculator = self.geo_calculator
        step_km: float = self.step_km
        max_points: int = self.max_points

        total_distance: float = geo.geodesic_distance(s_lat, s_lon, d_lat, d_lon)
        n_points: int = int(total_distance // step_km)

        if n_points + 2 > max_points:                            # Consider also the source and destination points
            n_points: int = max_points - 2     
            step_km: float = total_distance / (n_points + 1)

        bearing: float = geo.bearing(s_lat, s_lon, d_lat, d_lon)
        logger.debug(f"Interpolating route from ({s_lat}, {s_lon}) to ({d_lat}, {d_lon}) with {n_points + 2} steps of {step_km} km each. "
                     f"Bearing between source and destination: {bearing} degrees.")

        waypoints: List[Tuple[float, float]] = [(s_lat, s_lon)]  # Starting point
        
        for i in range(1, n_points + 1):
            step_distance: float = i * step_km
            step_lat, step_lon = geo.move(s_lat, s_lon, step_distance, bearing)
            waypoints.append((step_lat, step_lon))

        waypoints.append((d_lat, d_lon))                          # Destination point
        
        return waypoints, step_km, total_distance

    def calculate_wmi(self, wmi_input: WMIInputDTO) -> WMIValueDTO:
        if not self.use_traffic_service:
            logger.debug("Weather service not enabled: skipping WMI calculation.")
            return WMIValueDTO(value=0.0, computed=False)
        
        average_time_hours: float = wmi_input.route_average_time
        if average_time_hours <= 0:
            logger.warning(f"Route Average time is zero or negative: {average_time_hours}. Cannot calculate WMI.")
            return WMIValueDTO(value=0.0, computed=False)

        source: ig.Vertex = wmi_input.source
        destination: ig.Vertex = wmi_input.destination
        shipment_estimation_time: datetime = wmi_input.shipment_estimation_time
        departure_time: datetime = wmi_input.departure_time

        if departure_time - shipment_estimation_time > timedelta(hours=self.max_timedelta):
            logger.debug(f"Departure time {departure_time} exceeds max timedelta from estimation time {shipment_estimation_time}. Skipping WMI calculation.")
            return WMIValueDTO(value=0.0, computed=False)
        
        interpolation_result: Tuple[List[Tuple[float, float]], float, float] = self._interpolate_route(
            s_lat=source[LATITUDE_ATTR],
            s_lon=source[LONGITUDE_ATTR],
            d_lat=destination[LATITUDE_ATTR],
            d_lon=destination[LONGITUDE_ATTR]
        )
        waypoints: List[Tuple[float, float]] = interpolation_result[0]
        step_distance_km: float = interpolation_result[1]
        total_distance: float = interpolation_result[2]

        logger.debug(f"Interpolated {len(waypoints)} waypoints for WMI calculation with step distance {step_distance_km} km")
        
        average_speed_km_h: float = total_distance / average_time_hours
        logger.debug(f"Route distance: {total_distance} km, Average time: {average_time_hours} hours, Average speed: {average_speed_km_h} km/h")

        actual_time: datetime = departure_time
        
        weather_requests_data: List['WeatherRequest'] = []
        logger.debug(f"Preparing weather requests for {len(waypoints)} waypoints starting at {actual_time.isoformat()}")
        
        for lat, lon in waypoints:
            request: WeatherRequest = WeatherRequest(
                latitude=lat,
                longitude=lon,
                timestamp=actual_time
            )
            weather_requests_data.append(request)
            logger.debug(f"Weather request for waypoint ({lat}, {lon}) at time {actual_time.isoformat()}: {request}")

            actual_time += timedelta(hours=step_distance_km / average_time_hours)

        logger.debug(f"Finished preparing weather requests for {len(weather_requests_data)} waypoints at time {actual_time.isoformat()}")

        logger.debug("Invoking weather service to retrieve weather data for waypoints.")
        weather_results: List['WeatherResult'] = self.lambda_client.get_weather_data(weather_requests_data)
        logger.debug(f"Received {len(weather_results)} weather results from the service.")

        weather_validated_results: List['WeatherResult'] = [doc for doc in weather_results if doc is not None and doc.error is False]
        logger.debug(f"Filtered {len(weather_validated_results)} valid weather results from the service response.")
        if not weather_validated_results:
            logger.warning("No valid weather data found in the response. Returning empty WMI value.")
            return WMIValueDTO(value=0.0, computed=False)

        weather_codes: Set[str] = set()
        temperatures: List[float] = []
        for result in weather_validated_results:
            waypoint_codes: List[str] = [code.strip() for code in result.weather_codes.split(',') if code.strip()]
            weather_codes.update(waypoint_codes)
            temperatures.append(result.temperature_celsius)

        logger.debug(f"Collected {len(weather_codes)} weather codes ({weather_codes}), {len(temperatures)} temperatures ({temperatures})")

        wmi_calculation_input: WMICalculationInputDTO = WMICalculationInputDTO(
            weather_codes=list(weather_codes),
            temperature_celsius=temperatures,
        )
        wmi_calculation_dto: 'WMICalculationDTO' = self.calculator.calculate(wmi_calculation_input)
        
        logger.debug(f"WMI calculation result: {wmi_calculation_dto}")

        wmi_dto: WMI_DTO = WMI_DTO.from_wmi_calculation_dto(
            wmi_calculation_dto=wmi_calculation_dto,
            source_index=source.index,
            source_id=source[V_ID_ATTR],
            source_name=source['name'],
            destination_index=destination.index,
            destination_id=destination[V_ID_ATTR],
            destination_name=destination['name'],
            timestamp=departure_time,
            n_interpolation_points=len(waypoints),
            step_distance_km=step_distance_km
        )
        if self._meets_save_conditions(wmi_dto):
            self.wmi_data.append(wmi_dto)
            logger.debug(f"Stored WMI DTO: {wmi_dto}")
        else:
            logger.debug(f"Avoided storing WMI DTO: {wmi_dto}")

        return WMIValueDTO(value=wmi_calculation_dto.value, computed=True)