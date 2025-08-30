import pytest
from unittest.mock import create_autospec, MagicMock

from service.read_only_db_connector import ReadOnlyDBConnector

from model.alpha import AlphaType
from core.initializer.initializer import Initializer, InitializerResult
from core.initializer.tfst_initializer import TFSTInitializer, TFSTInitializerResult
from core.calculator.dt.dt_calculator import DTCalculator
from core.calculator.est.est_calculator import ESTCalculator
from core.calculator.cfdi.cfdi_calculator import CFDICalculator
from core.calculator.eodt.eodt_calculator import EODTCalculator
from core.calculator.edd.edd_calculator import EDDCalculator
from core.calculator.time_deviation.time_deviation_calculator import TimeDeviationCalculator

from core.query_handler.params.params_result import (
    HolidayParams,
    DTParams,
    AlphaParams,
    RTEstimatorParams,
    PTParams,
    TTParams,
    TFSTParams,
    TMISpeedParameters,
    TMIDistanceParameters,
    TMIParams,
    WMIParams,
    TimeDeviationParams,
    ParamsResult
)

@pytest.fixture
def mock_tfst_initializer():
    mock = create_autospec(TFSTInitializer)
    mock.initialize.return_value = TFSTInitializerResult(
        alpha_calculator=MagicMock(),
        pt_calculator=MagicMock(),
        tt_calculator=MagicMock(),
        tfst_calculator=MagicMock()
    )
    return mock

@pytest.fixture
def initializer(mock_tfst_initializer):
    return Initializer(tfst_initializer=mock_tfst_initializer)

@pytest.fixture
def fake_db_connector():
    class FakeReadOnlyDBConnector(ReadOnlyDBConnector):
        def __init__(self):
            self._session = MagicMock()

        @property
        def session(self):
            return self._session
        
    return FakeReadOnlyDBConnector()

def _build_params_result() -> ParamsResult:
    return ParamsResult(
        dt_params=DTParams(
            confidence=0.95,
            holidays_params=HolidayParams(
                consider_closure_holidays=True,
                consider_working_holidays=True,
                consider_weekends_holidays=False
            )
        ),
        tfst_params=TFSTParams(
            alpha_params=AlphaParams(
                const_alpha_value=0.42,
                alpha_type=AlphaType.EXP
            ),
            pt_params=PTParams(
                rte_estimator_params=RTEstimatorParams(model_mape=0.2, use_model=True),
                tmi_params=TMIParams(
                    speed_parameters=TMISpeedParameters.default(),
                    distance_parameters=TMIDistanceParameters.default(),
                    use_traffic_service=True,
                    traffic_max_timedelta=4.0
                ),
                wmi_params=WMIParams(
                    use_weather_service=True,
                    weather_max_timedelta=5.0,
                    step_distance_km=10.0,
                    max_points=100
                ),
                confidence=0.95,
                path_min_probability=0.1,
                max_paths=10,
                ext_data_min_probability=0.05
            ),
            tt_params=TTParams(confidence=0.9),
            tolerance=0.1
        ),
        time_deviation_params=TimeDeviationParams(
            dt_time_deviation_confidence=0.95,
            st_time_deviation_confidence=0.9
        ),
        parallelization=4
    )

def test_initializer_stores_dependency(mock_tfst_initializer):
    init = Initializer(tfst_initializer=mock_tfst_initializer)
    assert init.tfst_initializer is mock_tfst_initializer

def test_initialize_returns_correct_result_types(initializer, fake_db_connector):
    params = _build_params_result()

    result = initializer.initialize(
        params=params,
        maybe_ro_db_connector=fake_db_connector
    )

    assert isinstance(result, InitializerResult)
    assert isinstance(result.dt_calculator, DTCalculator)
    assert isinstance(result.tfst_initializer_result, TFSTInitializerResult)
    assert isinstance(result.est_calculator, ESTCalculator)
    assert isinstance(result.cfdi_calculator, CFDICalculator)
    assert isinstance(result.eodt_calculator, EODTCalculator)
    assert isinstance(result.edd_calculator, EDDCalculator)
    assert isinstance(result.time_deviation_calculator, TimeDeviationCalculator)

def test_initialize_delegates_to_tfst_initializer(mock_tfst_initializer, initializer, fake_db_connector):
    params = _build_params_result()

    initializer.initialize(
        params=params,
        maybe_ro_db_connector=fake_db_connector
    )

    mock_tfst_initializer.initialize.assert_called_once()
