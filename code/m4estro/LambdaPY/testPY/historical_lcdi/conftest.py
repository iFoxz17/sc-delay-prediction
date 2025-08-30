import pytest
import os
import sys

PLATFORM_COMM_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../platform_comm_layer/python/'))
if PLATFORM_COMM_LAYER_PATH not in sys.path:
    sys.path.insert(0, PLATFORM_COMM_LAYER_PATH)

STATS_LAYER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stats_layer/python/'))
if STATS_LAYER_PATH not in sys.path:
    sys.path.insert(0, STATS_LAYER_PATH)

HIST_LCDI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../historical_lcdi/'))
if HIST_LCDI_PATH not in sys.path:
    sys.path.insert(0, HIST_LCDI_PATH)


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "mock-region")
    monkeypatch.setenv("DATABASE_SECRET_ARN", "mock-secret-arn")