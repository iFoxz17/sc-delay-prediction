from typing import Dict, Any, TYPE_CHECKING, Optional
from dataclasses import dataclass
from datetime import datetime

from model.tmi import TransportationMode

from service.lambda_client.lambda_client import LambdaClient

from logger import get_logger
logger = get_logger(__name__)

if TYPE_CHECKING:
    import botocore.client

@dataclass(frozen=True)
class TrafficRequest:
    source_latitude: float
    source_longitude: float
    destination_latitude: float
    destination_longitude: float
    departure_time: datetime
    transportation_mode: TransportationMode

@dataclass(frozen=True)
class TrafficResult:
    distance_km: float
    travel_time_hours: float
    no_traffic_travel_time_hours: float
    traffic_delay_hours: float
    error: bool

class TrafficServiceLambdaClient(LambdaClient):
    def __init__(self, lambda_arn: str, lambda_client: Optional["botocore.client.BaseClient"] = None) -> None:
        super().__init__(lambda_arn=lambda_arn, lambda_client=lambda_client)

    def _empty_traffic_result(self) -> TrafficResult:
        return TrafficResult(
            distance_km=0.0,
            travel_time_hours=0.0,
            traffic_delay_hours=0.0,
            no_traffic_travel_time_hours=0.0,
            error=True
        )

    def get_traffic_data(self, request_data: TrafficRequest) -> TrafficResult:
        payload = {
            "service": "traffic",
            "action": "get",
            "data": {
                "source_latitude": request_data.source_latitude,
                "source_longitude": request_data.source_longitude,
                "destination_latitude": request_data.destination_latitude,
                "destination_longitude": request_data.destination_longitude,
                "departure_time": self._format_timestamp(request_data.departure_time),
                "transportation_mode": request_data.transportation_mode.value
            }
        }
        response_data: Dict[Any, Any] = super().invoke(payload)
        traffic_data: Dict[str, Any] = response_data.get("data", {})

        logger.debug(f"Received traffic data: {traffic_data}")

        if not traffic_data:
            logger.warning("No traffic data found in external API lambda response")
            return self._empty_traffic_result()
        
        try:
            traffic_result: TrafficResult = TrafficResult(
                distance_km=float(traffic_data["distance_km"]),
                travel_time_hours=float(traffic_data["travel_time_hours"]),
                no_traffic_travel_time_hours=float(traffic_data["no_traffic_travel_time_hours"]),
                traffic_delay_hours=float(traffic_data["traffic_delay_hours"]),
                error=False
            )
        except KeyError as e:
            logger.warning(f"Retrieved traffic data is missing a required key: {e}")
            return self._empty_traffic_result()

        return traffic_result