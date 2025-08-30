import pytest
from unittest.mock import Mock
import numpy as np

from core.calculator.tfst.pt.tmi.tmi_manager import TMIValueDTO
from core.calculator.tfst.pt.wmi.wmi_manager import WMIValueDTO

from core.calculator.tfst.pt.route_time.route_time_calculator import RouteTimeCalculator
from core.calculator.tfst.pt.route_time.route_time_input_dto import RouteTimeInputDTO
from core.calculator.tfst.pt.route_time.route_time_dto import RouteTimeDTO

MAPE = 0.6

@pytest.fixture
def mock_estimator():
    return Mock()

@pytest.fixture
def calculator(mock_estimator):
    return RouteTimeCalculator(estimator=mock_estimator, mape=MAPE)

def test_calculate_returns_first_prediction(calculator, mock_estimator):
    dto = RouteTimeInputDTO(
        latitude_source=1.0, longitude_source=2.0,
        latitude_destination=3.0, longitude_destination=4.0,
        distance=10.0,
        avg_oti=0.5, tmi=TMIValueDTO(value=0.3, computed=True), avg_tmi=1.5, wmi=WMIValueDTO(value=0.8, computed=True), avg_wmi=0.6,
    )
    confidence = 0.8

    # Mock prediction: estimator returns a list of predictions
    mock_estimator.predict.return_value = [99.0, 88.0]

    result: RouteTimeDTO = calculator.calculate(dto, confidence)

    assert np.isclose(result.lower, 99.0 * (1 - MAPE * confidence))
    assert np.isclose(result.upper, 99.0 * (1 + MAPE * confidence))
    mock_estimator.predict.assert_called_once_with(dto)
