import os

from utils.config import SC_GRAPH_BUCKET_NAME

from logger import get_logger
logger = get_logger(__name__)

def get_bucket_name() -> str:
    try:
        bucket_name: str = os.environ[SC_GRAPH_BUCKET_NAME]
    except KeyError:
        logger.error(f"Environment variable '{SC_GRAPH_BUCKET_NAME}' not set")
        raise

    return bucket_name