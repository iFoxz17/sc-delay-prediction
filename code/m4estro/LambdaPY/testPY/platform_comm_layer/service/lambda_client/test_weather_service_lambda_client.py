import pytest
from unittest.mock import MagicMock
import json
from datetime import datetime, timezone

from service.lambda_client.weather_service_lambda_client import (
    WeatherServiceLambdaClient,
    WeatherRequest,
    WeatherResult,
)

class DummyPayload:
    def __init__(self, data: dict):
        self._data = data

    def read(self):
        return json.dumps(self._data).encode("utf-8")

def make_lambda_response(payload_dict):
    return {"Payload": DummyPayload(payload_dict), "StatusCode": 200}


def test_get_weather_data_success():
    expected_data = [
        {
            "weather_codes": "1000",
            "temperature_celsius": 22.5,
            "humidity": 65.0,
            "wind_speed": 5.5,
            "visibility": 10.0,
            "error": False
        }
    ]

    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        "data": expected_data
    })

    client = WeatherServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    request = WeatherRequest(
        latitude=45.0,
        longitude=7.0,
        timestamp=datetime(2025, 7, 16, 12, 0, 0, tzinfo=timezone.utc),
        location_name="Test Location"
    )

    results = client.get_weather_data([request])
    assert isinstance(results, list)
    assert len(results) == 1
    result = results[0]

    assert isinstance(result, WeatherResult)
    assert result.weather_codes == expected_data[0]["weather_codes"]
    assert result.temperature_celsius == expected_data[0]["temperature_celsius"]
    assert result.humidity == expected_data[0]["humidity"]
    assert result.wind_speed == expected_data[0]["wind_speed"]
    assert result.visibility == expected_data[0]["visibility"]
    assert not result.error

    mock_lambda_client.invoke.assert_called_once()
    args, kwargs = mock_lambda_client.invoke.call_args
    payload = json.loads(kwargs["Payload"])
    assert payload["service"] == "weather"
    assert payload["action"] == "get"
    assert isinstance(payload["data"], list)
    assert payload["data"][0]["latitude"] == request.latitude
    assert payload["data"][0]["longitude"] == request.longitude
    timestamp = datetime.fromisoformat(payload["data"][0]["timestamp"])
    assert timestamp.isoformat(timespec='minutes') == request.timestamp.isoformat(timespec='minutes')
    assert payload["data"][0]["location_name"] == request.location_name


def test_get_weather_data_empty_data_list_returns_empty_results():
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        "data": []
    })

    client = WeatherServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    request = WeatherRequest(
        latitude=0.0,
        longitude=0.0,
        timestamp=datetime.now()
    )

    results = client.get_weather_data([request])
    assert isinstance(results, list)
    assert len(results) == 1
    result = results[0]
    assert result == WeatherResult("", 0.0, 0.0, 0.0, 0.0, error=True)


def test_get_weather_data_none_data_in_response():
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        "data": [None]
    })

    client = WeatherServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    request = WeatherRequest(
        latitude=1.0,
        longitude=2.0,
        timestamp=datetime.now()
    )

    results = client.get_weather_data([request])
    assert len(results) == 1
    assert results[0] == WeatherResult("", 0.0, 0.0, 0.0, 0.0, error=True)


def test_get_weather_data_missing_keys_returns_empty_result():
    incomplete_data = [
        {
            "weather_codes": "1000"
            # Missing temperature, humidity, wind_speed, visibility
        }
    ]

    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        "data": incomplete_data
    })

    client = WeatherServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    request = WeatherRequest(
        latitude=3.0,
        longitude=4.0,
        timestamp=datetime.now()
    )

    results = client.get_weather_data([request])
    assert len(results) == 1
    assert results[0] == WeatherResult("", 0.0, 0.0, 0.0, 0.0, error=True)


def test_get_weather_data_multiple_requests():
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.return_value = make_lambda_response({
        "success": True,
        "data": [
            {
                "weather_codes": "1000",
                "temperature_celsius": 25.0,
                "humidity": 50.0,
                "wind_speed": 3.0,
                "visibility": 8.0
            },
            {
                "weather_codes": "2000",
                "temperature_celsius": 18.0,
                "humidity": 80.0,
                "wind_speed": 6.0,
                "visibility": 5.0
            }
        ]
    })

    client = WeatherServiceLambdaClient(lambda_client=mock_lambda_client, lambda_arn="dummy-arn")

    requests = [
        WeatherRequest(
            latitude=10.0,
            longitude=10.0,
            timestamp=datetime.now()
        ),
        WeatherRequest(
            latitude=20.0,
            longitude=20.0,
            timestamp=datetime.now()
        )
    ]

    results = client.get_weather_data(requests)

    assert len(results) == 2
    assert results[0].weather_codes == "1000"
    assert results[1].weather_codes == "2000"
