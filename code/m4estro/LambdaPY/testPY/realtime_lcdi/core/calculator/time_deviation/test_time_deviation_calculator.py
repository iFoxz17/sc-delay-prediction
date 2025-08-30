import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO
from core.calculator.time_deviation.time_deviation_calculator import TimeDeviationCalculator
from core.calculator.time_deviation.time_deviation_input_dto import (
    TimeDeviationBaseInputDTO, TimeDeviationInputDTO, STDistributionDTO, STGammaDTO, STSampleDTO
)
from core.calculator.time_deviation.time_deviation_dto import TimeDeviationDTO
from core.calculator.dt.holiday.holiday_dto import HolidayResultDTO
from core.calculator.dt.dt_input_dto import DTGammaDTO, DTSampleDTO
from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.tfst.tfst_dto import TFSTCalculationDTO


@pytest.fixture
def calculator():
    return TimeDeviationCalculator(dispatch_confidence=0.95, shipment_confidence=0.9)


def build_dt_dto(elapsed_time=5.0, remaining_lower=2.0, remaining_upper=3.0):
    return DT_DTO(
        confidence=0.95,
        elapsed_time=elapsed_time,
        elapsed_working_time=elapsed_time,
        elapsed_holidays=MagicMock(spec=HolidayResultDTO),
        remaining_time_lower=remaining_lower,
        remaining_time=(remaining_lower + remaining_upper) / 2.0,
        remaining_time_upper=remaining_upper,
        remaining_working_time_lower=remaining_lower,
        remaining_working_time=(remaining_lower + remaining_upper) / 2.0,
        remaining_working_time_upper=remaining_upper,
        remaining_holidays=MagicMock(spec=HolidayResultDTO),
    )


@patch("core.calculator.time_deviation.time_deviation_calculator.compute_gamma_ci")
def test_calculate_with_gamma_dtos(mock_gamma_ci, calculator):
    shipment_time_threshold = 14.0
    mock_gamma_ci.side_effect = [
        (1.0, 4.0),  # DT
        (12.0, shipment_time_threshold),  # ST
    ]

    dt_dto = build_dt_dto()

    estimation_time = datetime.now(timezone.utc)
    event_time = estimation_time
    shipment_time = estimation_time - timedelta(hours=5)
    order_time = shipment_time - timedelta(hours=dt_dto.total_time)

    time_sequence = TimeSequenceDTO(
        order_time=order_time,
        shipment_time=shipment_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    input_dto = TimeDeviationInputDTO(
        td_partial_input=TimeDeviationBaseInputDTO(
            dt_distribution=DTGammaDTO(shape=2.0, scale=1.0, loc=0.0),
            st_distribution=STGammaDTO(shape=2.0, scale=1.5, loc=0.0),
        ),
        dt=dt_dto,
        tfst=TFSTCalculationDTO(lower=10.0, upper=12.0, alpha=0.5),
    )

    result = calculator.calculate(input_dto, time_sequence=time_sequence)

    expected = TimeDeviationDTO(
        dt_td_lower=dt_dto.total_time_lower - 4.0,  # 5 + 2 - 4 = 3
        dt_td_upper=dt_dto.total_time_upper - 4.0,  # 5 + 3 - 4 = 4
        st_td_lower=(10.0 + 5.0) - shipment_time_threshold,  # 15 - 14 = 1
        st_td_upper=(12.0 + 5.0) - shipment_time_threshold,  # 17 - 14 = 3
        dt_confidence=0.95,
        st_confidence=0.9
    )

    assert result == expected


@patch("core.calculator.time_deviation.time_deviation_calculator.compute_sample_ci")
def test_calculate_with_sample_dtos(mock_sample_ci, calculator):
    shipment_time_threshold = 14.0
    mock_sample_ci.side_effect = [
        (1.0, 4.0),  # DT
        (12.0, shipment_time_threshold),  # ST
    ]

    dt_dto = build_dt_dto()

    estimation_time = datetime.now(timezone.utc)
    event_time = estimation_time
    shipment_time = estimation_time - timedelta(hours=5)
    order_time = shipment_time - timedelta(hours=dt_dto.total_time)

    time_sequence = TimeSequenceDTO(
        order_time=order_time,
        shipment_time=shipment_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    input_dto = TimeDeviationInputDTO(
        td_partial_input=TimeDeviationBaseInputDTO(
            dt_distribution=DTSampleDTO(x=[2.0, 3.0, 4.0], mean=3.0),
            st_distribution=STSampleDTO(x=[5.0, 6.0, 7.0], mean=6.0),
        ),
        dt=dt_dto,
        tfst=TFSTCalculationDTO(lower=10.0, upper=12.0, alpha=0.5)
    )

    result = calculator.calculate(input_dto, time_sequence=time_sequence)

    expected = TimeDeviationDTO(
        dt_td_lower=dt_dto.total_time_lower - 4.0,  # 5 + 2 - 4 = 3
        dt_td_upper=dt_dto.total_time_upper - 4.0,  # 5 + 3 - 4 = 4
        st_td_lower=(10.0 + 5.0) - shipment_time_threshold,  # 15 - 14 = 1
        st_td_upper=(12.0 + 5.0) - shipment_time_threshold,  # 17 - 14 = 3
        dt_confidence=0.95,
        st_confidence=0.9
    )

    assert result == expected


def test_unsupported_dt_distribution_raises(calculator):
    class FakeDT:
        pass

    dt_dto = build_dt_dto()

    with pytest.raises(ValueError):
        calculator._calculate_dt_time_deviation(FakeDT(), dt=dt_dto)


def test_unsupported_st_distribution_raises(calculator):
    class FakeST:
        pass

    with pytest.raises(ValueError):
        calculator._calculate_st_time_deviation(
            st_distribution=FakeST(),
            tfst=TFSTCalculationDTO(lower=5.0, upper=10.0, alpha=0.5),
            shipment_time=datetime.now(timezone.utc),
            estimation_time=datetime.now(timezone.utc)
        )
