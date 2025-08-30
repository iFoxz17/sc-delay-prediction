import pytest
from unittest.mock import MagicMock
import json

from service.lambda_client.geo_service_lambda_client import GeoServiceLambdaClient, LocationResult

class DummyPayload:
    def __init__(self, data: dict):
        self._data = data

    def read(self):
        return json.dumps(self._data).encode("utf-8")

def make_lambda_response(payload_dict):
    return {"Payload": DummyPayload(payload_dict), "StatusCode": 200}

def test_get_location_data_success():
    expected_data = {
        "name": "New York",
        "city": "New York",
        "state": "NY",
        "country": "USA",
        "country_code": "US",
        "latitude": 40.7128,
        "longitude": -74.0060
    }

    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        "data": expected_data
    })

    client = GeoServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    result = client.get_location_data("New York", "USA")

    # Compare all fields of LocationResult with expected_data
    for key, value in expected_data.items():
        assert getattr(result, key) == value

    mock_lambda_client.invoke.assert_called_once()
    args, kwargs = mock_lambda_client.invoke.call_args
    payload = json.loads(kwargs["Payload"])
    assert payload["service"] == "location"
    assert payload["action"] == "get"
    assert payload["data"]["city"] == "New York"
    assert payload["data"]["country"] == "USA"

def test_get_location_data_invocation_exception():
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.side_effect = Exception("AWS Lambda invoke error")

    client = GeoServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    with pytest.raises(Exception, match="AWS Lambda invoke error"):
        client.get_location_data("City", "Country")

def test_get_location_data_api_response_unsuccessful():
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": False,
        "data": {}
    })

    client = GeoServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    with pytest.raises(ValueError):
        client.get_location_data("City", "Country")

def test_get_location_data_empty_data():
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        "data": None
    })

    client = GeoServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    with pytest.raises(ValueError):
        client.get_location_data("City", "Country")
