import pytest
import os
import sys

PLATFORM_COMM_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../platform_comm_layer/python/'))
if PLATFORM_COMM_LAYER_PATH not in sys.path:
    sys.path.insert(0, PLATFORM_COMM_LAYER_PATH)

GRAPH_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../graph_layer/python/'))
if GRAPH_LAYER_PATH not in sys.path:
    sys.path.insert(0, GRAPH_LAYER_PATH)

DOMAIN_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../domain_model/'))
if DOMAIN_MODEL_PATH not in sys.path:
    sys.path.insert(0, DOMAIN_MODEL_PATH)


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "mock-region")
    monkeypatch.setenv("DATABASE_SECRET_ARN", "mock-secret-arn")
    monkeypatch.setenv("EXTERNAL_API_LAMBDA_ARN", "mock-external-api-lambda-arn")
    monkeypatch.setenv("SC_GRAPH_BUCKET", "mock-sc-graph-bucket-name")