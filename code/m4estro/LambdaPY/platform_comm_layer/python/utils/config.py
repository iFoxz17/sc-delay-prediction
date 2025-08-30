from typing import Dict
from datetime import date, datetime
import os

AWS_REGION_KEY = 'AWS_REGION'
DATABASE_SECRET_ARN_KEY = 'DATABASE_SECRET_ARN'
EXTERNAL_API_LAMBDA_ARN_KEY = 'EXTERNAL_API_LAMBDA_ARN'
SC_GRAPH_BUCKET_NAME_KEY = 'SC_GRAPH_BUCKET'
RECONFIGURATION_QUEUE_URL_KEY = 'RECONFIGURATION_QUEUE_URL'
RT_ESTIMATOR_LAMBDA_ARN_KEY = 'RT_ESTIMATOR_LAMBDA_ARN'

COMMON_API_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "*",
    "Content-Type": "application/json"
}

def get_env(key: str) -> str:
    value = os.environ.get(key)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

WEEK_DAY_MAP: Dict[int, str] = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday"
}

def get_week_day(date: date | datetime) -> int:
    return date.weekday() + 1