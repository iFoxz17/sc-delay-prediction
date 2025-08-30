import pytest
from unittest.mock import MagicMock
import json
from datetime import datetime, timezone

from service.lambda_client.traffic_service_lambda_client import (
    TrafficServiceLambdaClient,
    TrafficRequest,
    TrafficResult,
)
from model.tmi import TransportationMode

class DummyPayload:
    def __init__(self, data: dict):
        self._data = data

    def read(self):
        return json.dumps(self._data).encode("utf-8")

def make_lambda_response(payload_dict):
    return {"Payload": DummyPayload(payload_dict), "StatusCode": 200}

def test_get_traffic_data_success():
    expected_data = {
        "distance_km": 100.5,
        "travel_time_hours": 2.5,
        "traffic_delay_hours": 0.5,
        "no_traffic_travel_time_hours": 2.0,
        "error": False
    }

    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        "data": expected_data
    })

    client = TrafficServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    request = TrafficRequest(
        source_latitude=45.0,
        source_longitude=7.0,
        destination_latitude=46.0,
        destination_longitude=8.0,
        departure_time=datetime(2025, 7, 16, 12, 0, 0, tzinfo=timezone.utc),
        transportation_mode=TransportationMode.ROAD
    )

    result = client.get_traffic_data(request)

    assert isinstance(result, TrafficResult)
    assert result.distance_km == expected_data["distance_km"]
    assert result.travel_time_hours == expected_data["travel_time_hours"]
    assert result.traffic_delay_hours == expected_data["traffic_delay_hours"]
    assert result.no_traffic_travel_time_hours == expected_data["no_traffic_travel_time_hours"]
    assert not result.error

    mock_lambda_client.invoke.assert_called_once()
    args, kwargs = mock_lambda_client.invoke.call_args
    payload = json.loads(kwargs["Payload"])
    assert payload["service"] == "traffic"
    assert payload["action"] == "get"
    assert payload["data"]["source_latitude"] == request.source_latitude
    departure_time = datetime.fromisoformat(payload["data"]["departure_time"])
    assert departure_time.isoformat(timespec='minutes') == request.departure_time.isoformat(timespec='minutes')
    assert payload["data"]["transportation_mode"] == request.transportation_mode.value

def test_get_traffic_data_no_data_key():
    # Simulate response without "data"
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        # "data" missing
    })

    client = TrafficServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    request = TrafficRequest(
        source_latitude=0,
        source_longitude=0,
        destination_latitude=0,
        destination_longitude=0,
        departure_time=datetime.now(),
        transportation_mode=TransportationMode.ROAD
    )

    data: TrafficResult = client.get_traffic_data(request)
    assert isinstance(data, TrafficResult)
    assert data.distance_km == 0.0
    assert data.travel_time_hours == 0.0
    assert data.traffic_delay_hours == 0.0
    assert data.no_traffic_travel_time_hours == 0.0
    assert data.error is True

def test_get_traffic_data_missing_keys():
    # Response data missing some keys, should return zeros
    incomplete_data = {
        "distance_km": 50.0,
        # missing travel_time_hours, traffic_delay_hours, no_traffic_travel_time_hours
    }
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        "data": incomplete_data
    })

    client = TrafficServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    request = TrafficRequest(
        source_latitude=0,
        source_longitude=0,
        destination_latitude=0,
        destination_longitude=0,
        departure_time=datetime.now(),
        transportation_mode=TransportationMode.ROAD
    )

    result = client.get_traffic_data(request)

    assert isinstance(result, TrafficResult)
    assert result.distance_km == 0.0
    assert result.travel_time_hours == 0.0
    assert result.traffic_delay_hours == 0.0
    assert result.no_traffic_travel_time_hours == 0.0

def test_get_traffic_data_invoke_raises():
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.side_effect = Exception("Lambda invocation error")

    client = TrafficServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    request = TrafficRequest(
        source_latitude=0,
        source_longitude=0,
        destination_latitude=0,
        destination_longitude=0,
        departure_time=datetime.now(),
        transportation_mode=TransportationMode.ROAD
    )

    with pytest.raises(Exception, match="Lambda invocation error"):
        client.get_traffic_data(request)
