from typing import Dict, TYPE_CHECKING, Optional
import json
import boto3

from logger import get_logger
from core.sc_graph.path_prob.path_prob_dp_manager import PathProbDPManager

if TYPE_CHECKING:
    import botocore.client

s3: 'botocore.client.BaseClient' = boto3.client('s3')

from graph_config import PATH_PROB_DP_MANAGER_KEY
logger = get_logger(__name__)

class S3PathProbDPManagerSerializer:
    def __init__(self):
        pass

    def serialize(self, dp_manager: PathProbDPManager, bucket_name: str, key: str = PATH_PROB_DP_MANAGER_KEY, force: bool = False) -> None:
        if not force and not dp_manager.is_updated():
            logger.debug("No PathProbDPManager update to save: skipping serialization")
            return
        
        try:
            dp_data: Dict = dp_manager.to_json()
        except Exception:
            logger.exception(f"Error converting PathProbDPManager to serializable format")
            raise

        logger.debug("PathProbDPManager converted to serializable format successfully")
        
        try:
            s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=json.dumps(dp_data).encode('utf-8'),
                ContentType='application/json'
            )
        except Exception:
            logger.exception(f"Error serializing PathProbDPManager data to {bucket_name}/{key}")
            raise
        
        logger.debug(f"PathProbDPManager serialized successfully to {bucket_name}/{key}")

    def deserialize(self, bucket_name: str, key: str = PATH_PROB_DP_MANAGER_KEY) -> Optional[PathProbDPManager]:
        try:
            # Check if the key exists
            s3.head_object(Bucket=bucket_name, Key=key)
        except Exception as e:
            logger.debug(f"PathProbDPManager not found at key {key} in bucket {bucket_name}")
            return None

        try:
            response = s3.get_object(Bucket=bucket_name, Key=key)
            content: str = response['Body'].read().decode('utf-8')
            dp_data: Dict = json.loads(content)
        except Exception:
            logger.exception(f"Error retrieving PathProbDPManager data from {bucket_name}/{key}")
            raise

        logger.debug(f"PathProbDPManager data retrieved successfully from {bucket_name}/{key}")
        
        try:
            dp_manager: PathProbDPManager = PathProbDPManager.from_json(dp_data)
        except Exception:
            logger.exception(f"Error initializing PathProbDPManager from data")
            raise
        
        logger.debug("PathProbDPManager initialized successfully")
        return dp_manager