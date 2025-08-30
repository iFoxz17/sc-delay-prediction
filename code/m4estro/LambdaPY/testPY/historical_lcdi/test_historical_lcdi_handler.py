import pytest
from unittest.mock import patch, MagicMock
import json
from historical_lcdi_handler import app, HISTORICAL_BASE_PATH

@pytest.fixture
def base_query():
    return {
        "site": "1",
        "supplier": "1",
        "carrier": "ups",
    }


def build_event(path, method="GET", query=None, body=None):
    return {
        "resource": path,
        "path": path,
        "httpMethod": method,
        "queryStringParameters": query,
        "body": json.dumps(body) if body else None,
        "isBase64Encoded": False
    }

# DRI
def test_get_dri_success(base_query):
    response_body = [{"site": {"id": 1}, "supplier": {"id": 1}, "indicators": {"DRI": 0.2}}]
    with patch("historical_lcdi_handler.calculate_dri", return_value=response_body):
        event = build_event(f"{HISTORICAL_BASE_PATH}/dri", query={"site": base_query["site"], "supplier": base_query["supplier"]})
        response = app.resolve(event, None)     # type: ignore
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == response_body

def test_get_dri_internal_error(base_query):
    with patch("historical_lcdi_handler.calculate_dri", side_effect=Exception("boom")):
        event = build_event(f"{HISTORICAL_BASE_PATH}/dri", query={"site": base_query["site"], "supplier": base_query["supplier"]})
        response = app.resolve(event, None) # type: ignore
        assert response["statusCode"] == 500
        assert "boom" in response["body"].lower()


# CLI
def test_get_cli_success(base_query):
    response_body = [{"carrier_name": "ups", "indicators": {"CLI": 0.1}}]
    with patch("historical_lcdi_handler.calculate_cli", return_value=response_body):
        event = build_event(f"{HISTORICAL_BASE_PATH}/cli", query={"carrier": base_query["carrier"]})
        response = app.resolve(event, None) # type: ignore
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == response_body

def test_get_cli_internal_error(base_query):
    with patch("historical_lcdi_handler.calculate_cli", side_effect=Exception("boom")):
        event = build_event(f"{HISTORICAL_BASE_PATH}/cli", query={"carrier": base_query["carrier"]})
        response = app.resolve(event, None) # type: ignore
        assert response["statusCode"] == 500
        assert "boom" in response["body"].lower()


# Dispatch time
def test_get_dispatch_time_success(base_query):
    response_body = [{"site": {"id": 1}, "supplier": {"id": 1}, "indicators": {"ADT": 5.0}, "DDI": {"lower": 3.0, "upper": 7.0}}]
    with patch("historical_lcdi_handler.calculate_dispatch_time", return_value=response_body):
        event = build_event(f"{HISTORICAL_BASE_PATH}/dispatch-time", query={"site": base_query["site"], "supplier": base_query["supplier"]})
        response = app.resolve(event, None)     # type: ignore
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == response_body

def test_get_dispatch_time_internal_error(base_query):
    with patch("historical_lcdi_handler.calculate_dispatch_time", side_effect=Exception("boom")):
        event = build_event(f"{HISTORICAL_BASE_PATH}/dispatch-time", query={"site": base_query["site"], "supplier": base_query["supplier"]})
        response = app.resolve(event, None)     # type: ignore
        assert response["statusCode"] == 500
        assert "boom" in response["body"].lower()


# Shipment time
def test_get_shipment_time_success(base_query):
    response_body = [{"site": {"id": 1}, "supplier": {"id": 1}, "carrier": "ups", "indicators": {"AST": 5.0}, "CTDI": {"lower": 3.0, "upper": 7.0}}]
    with patch("historical_lcdi_handler.calculate_shipment_time", return_value=response_body):
        event = build_event(f"{HISTORICAL_BASE_PATH}/shipment-time", query=base_query)
        response = app.resolve(event, None)     # type: ignore
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == response_body

def test_get_shipment_time_internal_error(base_query):
    with patch("historical_lcdi_handler.calculate_shipment_time", side_effect=Exception("boom")):
        event = build_event(f"{HISTORICAL_BASE_PATH}/shipment-time", query=base_query)
        response = app.resolve(event, None)     # type: ignore
        assert response["statusCode"] == 500
        assert "boom" in response["body"].lower()


# Historical LCDI
def test_get_historical_lcdi_success(base_query):
    dispatch = [{"dispatch": 1}]
    shipment = [{"shipment": 2}]
    dri = [{"dri": 3}]
    cli = [{"cli": 4}]
    aggregated = [{"lcdi": "ok"}]

    with patch("historical_lcdi_handler.calculate_dispatch_time", return_value=dispatch), \
         patch("historical_lcdi_handler.calculate_shipment_time", return_value=shipment), \
         patch("historical_lcdi_handler.calculate_dri", return_value=dri), \
         patch("historical_lcdi_handler.calculate_cli", return_value=cli), \
         patch("historical_lcdi_handler.HistoricalLCDIAggregator") as mock_agg:

        instance = MagicMock()
        instance.aggregate.return_value = aggregated
        mock_agg.return_value = instance

        event = build_event(f"{HISTORICAL_BASE_PATH}", query=base_query)
        response = app.resolve(event, None)     # type: ignore
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == aggregated


def test_get_historical_lcdi_internal_error(base_query):
    with patch("historical_lcdi_handler.calculate_dispatch_time", side_effect=Exception("boom")), \
         patch("historical_lcdi_handler.calculate_shipment_time", side_effect=Exception("boom")), \
         patch("historical_lcdi_handler.calculate_dri", side_effect=Exception("boom")), \
         patch("historical_lcdi_handler.calculate_cli", side_effect=Exception("boom")):

        event = build_event(f"{HISTORICAL_BASE_PATH}", query=base_query)
        response = app.resolve(event, None)     # type: ignore
        assert response["statusCode"] == 500
        assert "boom" in response["body"].lower()
