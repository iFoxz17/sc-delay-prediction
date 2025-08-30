import json
from typing import Any, Optional
import boto3

from utils.config import DATABASE_SECRET_ARN_KEY, AWS_REGION_KEY, get_env
from service.read_only_db_connector import ReadOnlyDBConnector
from service.db_connector import DBConnector

from logger import get_logger
logger = get_logger(__name__)

def get_db_credentials(secret_arn: str, region: str) -> dict[str, Any]:
    client = boto3.client('secretsmanager', region_name=region)
    secret_value = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(secret_value['SecretString'])
    return secret

def build_connection_url(config: dict[str, Any]) -> str:
    return (
        f"postgresql+psycopg2://{config['username']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['dbname']}"
    )

def get_db_connector(maybe_secret_arn: Optional[str] = None, maybe_region: Optional[str] = None, read_only: bool = False) -> DBConnector:
    secret_arn: str = maybe_secret_arn or get_env(DATABASE_SECRET_ARN_KEY)
    region: str = maybe_region or get_env(AWS_REGION_KEY)

    try:
        config = get_db_credentials(secret_arn, region)
        db_connection_url = build_connection_url(config)
    except Exception:
        logger.exception("Error during database connection setup")
        raise

    if read_only:
        return ReadOnlyDBConnector(db_connection_url)

    return DBConnector(db_connection_url)

def get_read_only_db_connector(maybe_secret_arn: Optional[str] = None, maybe_region: Optional[str] = None) -> ReadOnlyDBConnector:
    secret_arn: str = maybe_secret_arn or get_env(DATABASE_SECRET_ARN_KEY)
    region: str = maybe_region or get_env(AWS_REGION_KEY)
    
    db_connector: DBConnector = get_db_connector(secret_arn, region, read_only=True)
    if not isinstance(db_connector, ReadOnlyDBConnector):
        raise TypeError("Expected ReadOnlyDBConnector instance")
    
    return db_connector