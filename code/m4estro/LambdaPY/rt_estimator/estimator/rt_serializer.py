from typing import Any, Dict, Optional
import logging
from logging import Logger
import boto3
import os

from xgboost import Booster

from estimator.rt_estimator import RTEstimator

logger: Logger = logging.getLogger(__name__)
s3 = boto3.client('s3')

RT_ESTIMATOR_MODEL_KEY: str = os.environ.get('ROUTE_TIME_ESTIMATOR_MODEL_KEY', '')
BUCKET_NAME: str = os.environ.get('SC_GRAPH_BUCKET', '')

class S3RTEstimatorSerializer:
    def __init__(self, 
                 rt_estimator_model_key: Optional[str] = None,
                 bucket_name: Optional[str] = None
                 ) -> None:
        self.rt_estimator_model_key: str = rt_estimator_model_key or RT_ESTIMATOR_MODEL_KEY
        self.bucket_name: str = bucket_name or BUCKET_NAME

    def deserialize(self) -> RTEstimator:
        bucket_name: str = self.bucket_name
        key: str = self.rt_estimator_model_key
        
        try:
            response: Dict[str, Any] = s3.get_object(Bucket=bucket_name, Key=key)
            model_raw: str = response['Body'].read().decode('utf-8').strip()
        except Exception:
            logger.exception(f"Error retrieving route time estimator model data from {bucket_name}/{key}")
            raise
        
        logger.debug(f"Route time estimator model data retrieved successfully from {bucket_name}/{key}")
        
        try:
            model: Booster = Booster()
            model.load_model(bytearray(model_raw, 'utf-8'))
            rt_estimator: RTEstimator = RTEstimator(model=model)
        except Exception:
            logger.exception(f"Error initializing RouteTimeEstimator with model data")
            raise
        
        logger.debug("RouteTimeEstimator initialized successfully")
        return rt_estimator