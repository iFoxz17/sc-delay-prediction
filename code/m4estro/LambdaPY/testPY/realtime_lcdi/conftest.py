import pytest
import os
import sys

PLATFORM_COMM_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../platform_comm_layer/python/'))
if PLATFORM_COMM_LAYER_PATH not in sys.path:
    sys.path.insert(0, PLATFORM_COMM_LAYER_PATH)

GRAPH_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../graph_layer/python/'))
if GRAPH_LAYER_PATH not in sys.path:
    sys.path.insert(0, GRAPH_LAYER_PATH)

STATS_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stats_layer/python/'))
if STATS_LAYER_PATH not in sys.path:
    sys.path.insert(0, STATS_LAYER_PATH)

REALTIME_LCDI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../realtime_lcdi/'))
if REALTIME_LCDI_PATH not in sys.path:
    sys.path.insert(0, REALTIME_LCDI_PATH)


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "mock-region")
    monkeypatch.setenv("DATABASE_SECRET_ARN", "mock-secret-arn")
    monkeypatch.setenv("EXTERNAL_API_LAMBDA_ARN", "mock-external-api-lambda-arn")
    monkeypatch.setenv("SC_GRAPH_BUCKET", "mock-sc-graph-bucket-name")
    monkeypatch.setenv("RECONFIGURATION_QUEUE_URL", "https://dummy.queue")
    monkeypatch.setenv("ROUTE_TIME_ESTIMATOR_MODEL_KEY", "rt_estimator_xgboost.json")
    monkeypatch.setenv("RT_ESTIMATOR_LAMBDA_ARN", "mock-rt-estimator-lambda-arn")