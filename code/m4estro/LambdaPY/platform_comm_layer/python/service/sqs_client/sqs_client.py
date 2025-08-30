from typing import Optional, Dict, Any, TYPE_CHECKING
import boto3
import json

from utils.config import AWS_REGION_KEY, get_env

if TYPE_CHECKING:
    import botocore.client

from logger import get_logger
logger = get_logger(__name__)

class SqsClient():
    def __init__(self, queue_url: str, sqs_client: Optional["botocore.client.BaseClient"] = None) -> None:
        self.queue_url: str = queue_url
        self.sqs_client = sqs_client or boto3.client("sqs", region_name=get_env(AWS_REGION_KEY))

    def send_message(self, message: Dict[str, Any]) -> Dict[Any, Any]:
        queue_url: str = self.queue_url
        try:
            response: Dict[Any, Any] = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
            )
            if response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 200:
                logger.debug(f"Message sent to queue {queue_url} with id {response.get('MessageId')}")
            else:
                logger.error(f"Queue send failure: {response}")
                raise ValueError(f"Failed to send message to queue {queue_url}, response: {response}")
        except Exception:
            logger.exception(f"Error sending message to queue")
            raise

        return response