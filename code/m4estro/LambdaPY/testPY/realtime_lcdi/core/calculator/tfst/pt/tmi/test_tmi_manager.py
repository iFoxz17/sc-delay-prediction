import pytest
from unittest.mock import MagicMock

from datetime import datetime, timedelta
import igraph as ig

from core.calculator.tfst.pt.tmi.tmi_dto import TMIValueDTO
from core.calculator.tfst.pt.tmi.tmi_dto import TMIInputDTO
from core.calculator.tfst.pt.tmi.calculator.tmi_calculation_input_dto import TMICalculationInputDTO

from core.calculator.tfst.pt.tmi.tmi_manager import TMIManager
from model.tmi import TransportationMode

# Constants for testing
from graph_config import V_ID_ATTR, LATITUDE_ATTR, LONGITUDE_ATTR

@pytest.fixture
def graph():
    g = ig.Graph()
    g.add_vertices(2)
    g.vs[0][V_ID_ATTR] = "SRC"
    g.vs[0]["name"] = "SourceCity"
    g.vs[0][LATITUDE_ATTR] = 45.0
    g.vs[0][LONGITUDE_ATTR] = 9.0

    g.vs[1][V_ID_ATTR] = "DST"
    g.vs[1]["name"] = "DestinationCity"
    g.vs[1][LATITUDE_ATTR] = 46.0
    g.vs[1][LONGITUDE_ATTR] = 10.0

    return g

@pytest.fixture
def mock_lambda_client():
    mock = MagicMock()
    mock.get_traffic_data.return_value = MagicMock(
        distance_km=120.0,
        travel_time_hours=2.5,
        no_traffic_travel_time_hours=2.0,
        error=False
    )
    return mock

@pytest.fixture
def mock_tmi_calculator():
    mock = MagicMock()
    mock.calculate.return_value = MagicMock(value=0.42, transportation_mode=TransportationMode.ROAD)
    return mock

@pytest.fixture
def tmi_manager(mock_lambda_client, mock_tmi_calculator):
    return TMIManager(
        lambda_client=mock_lambda_client,
        calculator=mock_tmi_calculator,
        use_traffic_service=True,
        max_timedelta=3.0  # hours
    )

def make_tmi_input(graph, departure_time_delta=2):
    return TMIInputDTO(
        source=graph.vs[0],
        destination=graph.vs[1],
        route_geodesic_distance=100.0,
        route_average_time=3.0,
        shipment_estimation_time=datetime.now(),
        departure_time=datetime.now() + timedelta(hours=departure_time_delta)
    )

def test_calculate_tmi_returns_computed_result(tmi_manager, graph):
    tmi_input = make_tmi_input(graph)

    result = tmi_manager.calculate_tmi(tmi_input)

    assert isinstance(result, TMIValueDTO)
    assert result.computed is True
    assert result.value == 0.42
    assert len(tmi_manager.tmi_data) == 1

def test_calculate_tmi_skips_if_traffic_service_disabled(mock_lambda_client, mock_tmi_calculator, graph):
    manager = TMIManager(
        lambda_client=mock_lambda_client,
        calculator=mock_tmi_calculator,
        use_traffic_service=False,
        max_timedelta=3.0
    )
    tmi_input = make_tmi_input(graph)

    result = manager.calculate_tmi(tmi_input)

    assert isinstance(result, TMIValueDTO)
    assert result.computed is False
    assert result.value == 0.0
    assert manager.tmi_data == []

def test_calculate_tmi_skips_if_departure_time_exceeds_max_timedelta(tmi_manager, graph):
    tmi_input = make_tmi_input(graph, departure_time_delta=5)  # 5 hours later
    
    result = tmi_manager.calculate_tmi(tmi_input)

    assert isinstance(result, TMIValueDTO)
    assert result.computed is False
    assert result.value == 0.0
    assert tmi_manager.tmi_data == []

def test_initialize_resets_tmi_data(tmi_manager, graph):
    tmi_input = make_tmi_input(graph)
    tmi_manager.calculate_tmi(tmi_input)

    assert len(tmi_manager.tmi_data) == 1

    tmi_manager.initialize()
    assert tmi_manager.tmi_data == []
