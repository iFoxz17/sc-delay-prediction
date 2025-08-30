import pytest
from unittest.mock import create_autospec, MagicMock

from core.initializer.tfst_initializer import TFSTInitializer, TFSTInitializerResult
from core.sc_graph.sc_graph import SCGraph
from core.calculator.tfst.pt.route_time.route_time_estimator import RouteTimeEstimator
from core.calculator.tfst.pt.pt_calculator import PTCalculator
from core.calculator.tfst.tt.tt_calculator import TTCalculator
from core.calculator.tfst.alpha.alpha_calculator import AlphaCalculator
from core.calculator.tfst.tfst_calculator import TFSTCalculator
from core.initializer.alpha_initializer import AlphaInitializer

from core.query_handler.params.params_result import TFSTParams, PTParams, TTParams, AlphaParams

@pytest.fixture
def mock_graph():
    return create_autospec(SCGraph)

@pytest.fixture
def mock_alpha_initializer():
    mock_alpha_init = create_autospec(AlphaInitializer)
    # Mock the .initialize() method to return an instance of AlphaCalculator (or subclass)
    mock_alpha_init.initialize.return_value = create_autospec(AlphaCalculator)
    return mock_alpha_init

@pytest.fixture
def initializer(mock_graph, mock_alpha_initializer):
    return TFSTInitializer(sc_graph=mock_graph, alpha_initializer=mock_alpha_initializer)

def make_params():
    # Provide simple dummy instances with minimal required attributes for the test
    alpha_params = AlphaParams(alpha_type=MagicMock(), const_alpha_value=0.2)  # alpha_type won't be used due to mocking
    pt_params = PTParams(
        rte_estimator_params=MagicMock(model_mape=0.1),
        tmi_params=MagicMock(
            speed_parameters={},
            distance_parameters={},
            use_traffic_service=False,
            traffic_max_timedelta=0
        ),
        wmi_params=MagicMock(),
        path_min_probability=0.5,
        max_paths=10,
        ext_data_min_probability=0.1,
        confidence=0.95
    )
    tt_params = TTParams(confidence=0.95)
    return TFSTParams(alpha_params=alpha_params, pt_params=pt_params, tt_params=tt_params, tolerance=0.1)

def test_initialize_returns_all_calculators(initializer):
    tfst_params = make_params()
    result = initializer.initialize(tfst_params)

    assert isinstance(result, TFSTInitializerResult)

    # The AlphaCalculator returned is a mock but type check is fine
    assert isinstance(result.alpha_calculator, AlphaCalculator)
    assert isinstance(result.pt_calculator, PTCalculator)
    assert isinstance(result.tt_calculator, TTCalculator)
    assert isinstance(result.tfst_calculator, TFSTCalculator)

def test_initializer_stores_dependencies(mock_graph, mock_alpha_initializer):
    initializer = TFSTInitializer(sc_graph=mock_graph, alpha_initializer=mock_alpha_initializer)
    assert initializer.sc_graph is mock_graph
    assert initializer.alpha_initializer is mock_alpha_initializer
