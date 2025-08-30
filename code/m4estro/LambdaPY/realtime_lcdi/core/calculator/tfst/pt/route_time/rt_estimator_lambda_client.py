from typing import Dict, Any, TYPE_CHECKING, Optional, List
import json
from dataclasses import dataclass, asdict

from service.lambda_client.lambda_client import LambdaClient

from core.calculator.tfst.pt.route_time.route_time_input_dto import RouteTimeInputDTO

from logger import get_logger
logger = get_logger(__name__)

if TYPE_CHECKING:
    import botocore.client

@dataclass(frozen=True)
class RTEstimationRequest:
    latitude_source: float
    longitude_source: float
    latitude_destination: float
    longitude_destination: float
    distance: float
    avg_tmi: float
    tmi: float
    avg_wmi: float
    wmi: float
    avg_oti: float

    @staticmethod
    def from_route_time_input_dto(dto: "RouteTimeInputDTO") -> "RTEstimationRequest":
        return RTEstimationRequest(
            latitude_source=dto.latitude_source,
            longitude_source=dto.longitude_source,
            latitude_destination=dto.latitude_destination,
            longitude_destination=dto.longitude_destination,
            distance=dto.distance,
            avg_tmi=dto.avg_tmi,
            tmi=dto.tmi.value,
            avg_wmi=dto.avg_wmi,
            wmi=dto.wmi.value,
            avg_oti=dto.avg_oti
        )

@dataclass(frozen=True)
class RTEstimationBatchRequest:
    batch: List[RTEstimationRequest]

@dataclass(frozen=True)
class RTEstimatorResponse:
    time: float

@dataclass(frozen=True)
class RTEstimatorBatchResponse:
    batch: List[RTEstimatorResponse]

class RTEstimatorLambdaClient(LambdaClient):
    def __init__(self, lambda_arn: str, lambda_client: Optional["botocore.client.BaseClient"] = None) -> None:
        super().__init__(lambda_arn=lambda_arn, lambda_client=lambda_client)

    def get_rt_estimation(self, request_data: RTEstimationBatchRequest) -> Optional[RTEstimatorBatchResponse]:
        payload = {
            "batch": [asdict(rt_est_request) for rt_est_request in request_data.batch],
        }
        response_data: Dict[Any, Any] = super().invoke(payload)
        logger.debug(f"Received RT estimation data: {response_data}")

        if not response_data:
            logger.warning("No RT estimation data found in rt_estimation API lambda response")
            return None
        
        code: int = response_data["statusCode"]
        if code != 200:
            logger.warning(f"RT estimation API lambda returned error code {code}: {response_data.get('body', 'No body in response')}")
            return None
        
        body_raw: str = response_data.get("body", "")
        if not body_raw:
            logger.warning("No body found in RT estimation API lambda response")
            return None
        
        try:
            body_parsed: Dict[str, Any] = json.loads(body_raw)
        except json.JSONDecodeError as e:
            logger.warning(f"Error decoding JSON from RT estimation API lambda response: {e}")
            return None

        prediction_data: List[Dict[str, float]] = body_parsed["predictions"]["batch"]

        try:
            rt_estimation_result: RTEstimatorBatchResponse = RTEstimatorBatchResponse(
                [
                    RTEstimatorResponse(time=float(rt_estimation_data["time"])) 
                    for rt_estimation_data in prediction_data
                ]
            )
        except Exception as e:
            logger.warning(f"Error during RT estimation result parsing: {e}")
            return None

        logger.debug(f"Parsed RT estimation result: {rt_estimation_result}")
        return rt_estimation_result