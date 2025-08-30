import pytest
from unittest.mock import Mock, create_autospec
from datetime import datetime, timedelta, timezone
import igraph as ig

from core.calculator.tfst.pt.wmi.wmi_manager import WMIManager
from core.query_handler.params.params_result import WMIParams
from core.calculator.tfst.pt.wmi.wmi_dto import WMIValueDTO, WMIInputDTO, WMI_DTO
from core.calculator.tfst.pt.wmi.calculator.wmi_calculation_input_dto import WMICalculationInputDTO
from core.calculator.tfst.pt.wmi.calculator.wmi_calculation_dto import WMICalculationDTO
from service.lambda_client.weather_service_lambda_client import WeatherRequest, WeatherResult
from geo_calculator import GeoCalculator

from graph_config import LATITUDE_ATTR, LONGITUDE_ATTR, V_ID_ATTR
from core.calculator.tfst.pt.wmi.calculator.wmi_calculator import By


@pytest.fixture
def default_params():
    return WMIParams(
        use_weather_service=True,
        weather_max_timedelta=5.0,  # hours
        step_distance_km=50.0,
        max_points=3,
    )


@pytest.fixture
def graph_vertices():
    graph = ig.Graph()
    graph.add_vertices(2)
    
    source = graph.vs[0]
    source[LATITUDE_ATTR] = 45.0
    source[LONGITUDE_ATTR] = 9.0
    source[V_ID_ATTR] = "S1"
    source["name"] = "Source"

    destination = graph.vs[1]
    destination[LATITUDE_ATTR] = 46.0
    destination[LONGITUDE_ATTR] = 10.0
    destination[V_ID_ATTR] = "D1"
    destination["name"] = "Destination"
    return source, destination


def test_weather_service_disabled(graph_vertices):
    default_params = WMIParams(
        use_weather_service=False,
        weather_max_timedelta=5.0,  # hours
        step_distance_km=50.0,
        max_points=10,
    )

    lambda_client = Mock()
    calculator = Mock()

    manager = WMIManager(lambda_client, calculator, default_params)
    source, destination = graph_vertices

    input_dto = WMIInputDTO(
        route_average_time=2.0,
        source=source,
        destination=destination,
        shipment_estimation_time=datetime.now(timezone.utc),
        departure_time=datetime.now(timezone.utc),
    )

    result = manager.calculate_wmi(input_dto)

    assert isinstance(result, WMIValueDTO)
    assert result.value == 0.0
    assert result.computed is False


def test_negative_average_time(default_params, graph_vertices):
    lambda_client = Mock()
    calculator = Mock()
    manager = WMIManager(lambda_client, calculator, default_params)
    source, destination = graph_vertices

    input_dto = WMIInputDTO(
        route_average_time=-1.0,
        source=source,
        destination=destination,
        shipment_estimation_time=datetime.now(timezone.utc),
        departure_time=datetime.now(timezone.utc),
    )

    result = manager.calculate_wmi(input_dto)

    assert result.value == 0.0
    assert not result.computed


def test_timedelta_exceeded(default_params, graph_vertices):
    lambda_client = Mock()
    calculator = Mock()
    manager = WMIManager(lambda_client, calculator, default_params)
    source, destination = graph_vertices

    now = datetime.now(timezone.utc)
    input_dto = WMIInputDTO(
        route_average_time=1.0,
        source=source,
        destination=destination,
        shipment_estimation_time=now,
        departure_time=now + timedelta(hours=6),  # exceeds max timedelta
    )

    result = manager.calculate_wmi(input_dto)

    assert result.value == 0.0
    assert not result.computed


def test_valid_weather_result(default_params, graph_vertices):
    lambda_client = Mock()
    calculator = Mock()
    geo_calculator = GeoCalculator()

    # Patch geodesic and bearing to simplify
    geo_calculator.geodesic_distance = Mock(return_value=100)
    geo_calculator.bearing = Mock(return_value=45)
    geo_calculator.move = Mock(return_value=(45.5, 9.5))

    manager = WMIManager(lambda_client, calculator, default_params, maybe_geo_calculator=geo_calculator)
    source, destination = graph_vertices

    now = datetime.now(timezone.utc)
    input_dto = WMIInputDTO(
        route_average_time=2.0,
        source=source,
        destination=destination,
        shipment_estimation_time=now,
        departure_time=now + timedelta(hours=1),
    )

    # One valid weather result
    weather_result = WeatherResult(
        weather_codes="rain",
        temperature_celsius=15.0,
        humidity=80,
        wind_speed=10.0,
        visibility=10.0,
        error=False
    )
    lambda_client.get_weather_data.return_value = [weather_result]

    calculator.calculate.return_value = WMICalculationDTO(
        value=0.42,
        weather_code="rain",
        weather_description="Rain",
        temperature_celsius=15.0,
        by=By.WEATHER_CONDITION
    )

    result = manager.calculate_wmi(input_dto)

    assert result.computed is True
    assert result.value == 0.42
    lambda_client.get_weather_data.assert_called_once()
    calculator.calculate.assert_called_once()


def test_no_valid_weather_results(default_params, graph_vertices):
    lambda_client = Mock()
    calculator = Mock()
    geo_calculator = GeoCalculator()
    geo_calculator.geodesic_distance = Mock(return_value=50)
    geo_calculator.bearing = Mock(return_value=45)
    geo_calculator.move = Mock(return_value=(45.5, 9.5))

    manager = WMIManager(lambda_client, calculator, default_params, maybe_geo_calculator=geo_calculator)
    source, destination = graph_vertices

    now = datetime.now(timezone.utc)
    input_dto = WMIInputDTO(
        route_average_time=1.5,
        source=source,
        destination=destination,
        shipment_estimation_time=now,
        departure_time=now + timedelta(hours=1),
    )

    # All weather results are errors
    lambda_client.get_weather_data.return_value = [
        WeatherResult(weather_codes="", temperature_celsius=0.0, error=True, humidity=0.0, wind_speed=0.0, visibility=0.0),
    ]

    result = manager.calculate_wmi(input_dto)

    assert result.computed is False
    assert result.value == 0.0
