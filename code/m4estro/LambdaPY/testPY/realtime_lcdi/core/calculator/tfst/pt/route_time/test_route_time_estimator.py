import pytest
import numpy as np
from unittest.mock import Mock

from core.calculator.tfst.pt.tmi.tmi_manager import TMIValueDTO
from core.calculator.tfst.pt.wmi.wmi_manager import WMIValueDTO
from core.calculator.tfst.pt.route_time.route_time_estimator import RouteTimeEstimator
from core.calculator.tfst.pt.route_time.route_time_input_dto import RouteTimeInputDTO
from core.calculator.tfst.pt.route_time.rt_estimator_lambda_client import (
    RTEstimatorLambdaClient,
    RTEstimationRequest,
    RTEstimatorBatchResponse,
    RTEstimatorResponse
)

@pytest.fixture
def mock_client():
    return Mock(spec=RTEstimatorLambdaClient)

@pytest.fixture
def estimator(mock_client):
    return RouteTimeEstimator(rt_estimator_client=mock_client)

def test_predict_single_computed(estimator, mock_client):
    dto = RouteTimeInputDTO(
        latitude_source=10.0,
        longitude_source=20.0,
        latitude_destination=30.0,
        longitude_destination=40.0,
        distance=100.0,
        avg_oti=1.0,
        tmi=TMIValueDTO(value=2.0, computed=True),
        avg_tmi=3.0,
        wmi=WMIValueDTO(value=4.0, computed=True),
        avg_wmi=5.0
    )

    mock_client.get_rt_estimation.return_value = RTEstimatorBatchResponse(
        batch=[RTEstimatorResponse(time=42.0)]
    )

    result = estimator.predict(dto)

    assert np.allclose(result, np.array([42.0]))
    mock_client.get_rt_estimation.assert_called_once()

def test_predict_single_not_computed(estimator, mock_client):
    dto = RouteTimeInputDTO(
        latitude_source=10.0,
        longitude_source=20.0,
        latitude_destination=30.0,
        longitude_destination=40.0,
        distance=100.0,
        avg_oti=1.0,
        tmi=TMIValueDTO(value=2.0, computed=False),
        avg_tmi=3.0,
        wmi=WMIValueDTO(value=4.0, computed=True),
        avg_wmi=5.0
    )

    result = estimator.predict(dto)

    assert np.allclose(result, np.array([1.0]))
    mock_client.get_rt_estimation.assert_not_called()

def test_predict_multiple_dtos(estimator, mock_client):
    dtos = [
        RouteTimeInputDTO(
            latitude_source=0.0, longitude_source=0.0,
            latitude_destination=0.0, longitude_destination=0.0,
            distance=10.0,
            avg_oti=1.0,
            tmi=TMIValueDTO(value=2.0, computed=True),
            avg_tmi=3.0,
            wmi=WMIValueDTO(value=4.0, computed=True),
            avg_wmi=5.0
        ),
        RouteTimeInputDTO(
            latitude_source=0.0, longitude_source=0.0,
            latitude_destination=0.0, longitude_destination=0.0,
            distance=20.0,
            avg_oti=10.0,
            tmi=TMIValueDTO(value=20.0, computed=False),  # Not computed
            avg_tmi=30.0,
            wmi=WMIValueDTO(value=40.0, computed=True),
            avg_wmi=50.0
        )
    ]

    mock_client.get_rt_estimation.return_value = RTEstimatorBatchResponse(
        batch=[RTEstimatorResponse(time=99.0)]
    )

    result = estimator.predict(dtos)

    assert np.allclose(result, np.array([99.0, 10.0]))
    mock_client.get_rt_estimation.assert_called_once()
