from typing import Dict, Any, TYPE_CHECKING, Optional, List
from dataclasses import dataclass
from datetime import datetime

from service.lambda_client.lambda_client import LambdaClient

from logger import get_logger
logger = get_logger(__name__)

if TYPE_CHECKING:
    import botocore.client

@dataclass(frozen=True)
class WeatherRequest:
    latitude: float
    longitude: float
    timestamp: datetime
    location_name: Optional[str] = None

@dataclass(frozen=True)
class WeatherResult:
    weather_codes: str
    temperature_celsius: float
    humidity: float
    wind_speed: float
    visibility: float
    error: bool

class WeatherServiceLambdaClient(LambdaClient):
    def __init__(self, lambda_arn: str, lambda_client: Optional["botocore.client.BaseClient"] = None) -> None:
        super().__init__(lambda_arn=lambda_arn, lambda_client=lambda_client)

    def _empty_single_weather_result(self) -> WeatherResult:
        return WeatherResult(
            weather_codes="",
            temperature_celsius=0.0,
            humidity=0.0,
            wind_speed=0.0,
            visibility=0.0,
            error=True
        )

    def _empty_weather_result(self, n: int) -> list[WeatherResult]:
        return [self._empty_single_weather_result() for _ in range(n)]
    
    def _build_request_payload_data(self, request_data: WeatherRequest) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "latitude": request_data.latitude,
            "longitude": request_data.longitude,
            "timestamp": self._format_timestamp(request_data.timestamp)
        }

        if request_data.location_name:
            payload["location_name"] = request_data.location_name
        
        return payload

    def get_weather_data(self, request_data: List[WeatherRequest]) -> List[WeatherResult]:
        payload = {
            "service": "weather",
            "action": "get",
            "data": [self._build_request_payload_data(req) for req in request_data]
        }
        response_data: Dict[Any, Any] = super().invoke(payload)
        weather_data: List[Optional[Dict[str, Any]]] = response_data.get("data", [])

        logger.debug(f"Received weather data: {weather_data}")

        if not weather_data:
            logger.warning("No weather data found in external API lambda response")
            return self._empty_weather_result(len(request_data))
        
        weather_results: List[WeatherResult] = []
        try:
            for doc in weather_data:
                if doc is None:
                    logger.warning("Received None document in weather data")
                    weather_results.append(self._empty_single_weather_result())
                    continue

                result: WeatherResult = WeatherResult(
                    weather_codes=doc["weather_codes"],
                    temperature_celsius=float(doc["temperature_celsius"]),
                    humidity=float(doc["humidity"]),
                    wind_speed=float(doc["wind_speed"]),
                    visibility=float(doc["visibility"]),
                    error=False
                )
                weather_results.append(result)
        except KeyError as e:
            logger.error(f"Retrieved weather data is missing a required key: {e}")
            weather_results.append(self._empty_single_weather_result())

        return weather_results