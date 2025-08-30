from typing import Dict, Any, TYPE_CHECKING, Optional
from datetime import datetime, timezone
import json
import boto3

from utils.config import AWS_REGION_KEY, get_env

from logger import get_logger
logger = get_logger(__name__)

if TYPE_CHECKING:
    import botocore.client

class LambdaClient:
    def __init__(self, lambda_arn: str, lambda_client: Optional["botocore.client.BaseClient"] = None) -> None:
        self.lambda_arn: str = lambda_arn
        self.lambda_client: "botocore.client.BaseClient" = lambda_client or boto3.client("lambda", region_name=get_env(AWS_REGION_KEY))

    def _format_timestamp(self, timestamp: datetime) -> str:
        utc_timestamp: datetime = timestamp.astimezone(timezone.utc)
        return utc_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

    def invoke(self, payload: Dict[Any, Any]) -> Dict[Any, Any]:
        try:
            logger.debug(f"Invoking Lambda function {self.lambda_arn} with payload: {payload}")
            response: Dict = self.lambda_client.invoke(
                FunctionName=self.lambda_arn,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload)
            )
        except Exception:
            logger.exception("API call failed")
            raise
        
        status_code = response.get("StatusCode")
        if status_code != 200:
            logger.error(f"Lambda invocation failed with status code {status_code}")
            raise RuntimeError(f"Invocation failed: status code {status_code}")
            
        result: Dict[str, Any] = json.loads(response["Payload"].read().decode("utf-8"))
        return result

        
