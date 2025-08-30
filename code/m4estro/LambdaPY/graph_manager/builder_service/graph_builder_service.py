from typing import Dict, TYPE_CHECKING
import igraph as ig
import boto3

from service.db_utils import get_db_credentials, build_connection_url
from serializer.s3_graph_serializer import S3GraphSerializer
from utils.config import DATABASE_SECRET_ARN_KEY, AWS_REGION_KEY, SC_GRAPH_BUCKET_NAME_KEY, get_env
from graph_config import PATH_DP_MANAGER_KEY, PATH_PROB_DP_MANAGER_KEY

from builder_service.graph_builder import GraphBuilder
from builder_service.exception.s3_bucket_object_deletion_exception import S3BucketObjectDeletionException

if TYPE_CHECKING:
    import botocore.client

s3: 'botocore.client.BaseClient' = boto3.client('s3')

from logger import get_logger
logger = get_logger(__name__)

def _delete_s3_bucket_object(bucket_name: str, key: str) -> None:
    try:
        s3.head_object(Bucket=bucket_name, Key=key)
    except Exception as e:
        logger.debug(f"No object found at {bucket_name}/{key}, skipping deletion")
        return
    
    s3.delete_object(Bucket=bucket_name, Key=key)
    logger.debug(f"Object at {bucket_name}/{key} deleted successfully")

def build_graph() -> None:    
    try:
        config: Dict = get_db_credentials(secret_arn=get_env(DATABASE_SECRET_ARN_KEY), region=get_env(AWS_REGION_KEY))
        db_connection_url: str = build_connection_url(config)
    except Exception:
        logger.exception("Error during database connection setup")
        raise
    
    logger.debug(f"Retrieved database connection URL: {db_connection_url}")
    
    bucket_name: str = get_env(SC_GRAPH_BUCKET_NAME_KEY)
    logger.debug(f"Retrieved bucket name: {bucket_name}")
    
    builder: GraphBuilder = GraphBuilder(db_connection_url)
    try:
        g: ig.Graph = builder.build()
    except Exception:
        logger.exception("Error during graph building")
        raise
    
    logger.debug("Graph built successfully")
    
    try:
        serializer: S3GraphSerializer = S3GraphSerializer()
        serializer.serialize(g)
    except Exception:
        logger.exception("Error during graph serialization")
        raise

    for key in (PATH_DP_MANAGER_KEY, PATH_PROB_DP_MANAGER_KEY):
        try:
            _delete_s3_bucket_object(bucket_name, key)
        except Exception:
            logger.exception(f"Could not delete object at {bucket_name}/{key}")
            raise S3BucketObjectDeletionException(bucket_name, key)