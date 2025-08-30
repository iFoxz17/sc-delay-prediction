from typing import Dict, Any, TYPE_CHECKING, Optional
from dataclasses import dataclass

from service.lambda_client.lambda_client import LambdaClient

from logger import get_logger
logger = get_logger(__name__)

if TYPE_CHECKING:
    import botocore.client

@dataclass(frozen=True)
class LocationResult:
    name: str
    city: str
    state: Optional[str]
    country: str
    country_code: str
    latitude: float
    longitude: float

class GeoServiceLambdaClient(LambdaClient):
    def __init__(self, lambda_arn: str, lambda_client: Optional["botocore.client.BaseClient"] = None) -> None:
        super().__init__(lambda_arn=lambda_arn, lambda_client=lambda_client)

    def get_location_data(self, city: str, country: str) -> "LocationResult":
        payload = {
            "service": "location",
            "action": "get",
            "data": {"city": city, "country": country}
        }
        response_data: Dict[Any, Any] = super().invoke(payload)
        location_data: Dict[str, Any] = response_data.get("data", {})

        logger.debug(f"Received location data: {location_data}")

        if not location_data:
            logger.error("No location data found in external API lambda response")
            raise ValueError("No location data found in external API lambda response")

        return LocationResult(
            name=location_data["name"],
            city=location_data["city"],
            state=location_data.get("state"),
            country=location_data["country"],
            country_code=location_data["country_code"],
            latitude=location_data["latitude"],
            longitude=location_data["longitude"]
        )