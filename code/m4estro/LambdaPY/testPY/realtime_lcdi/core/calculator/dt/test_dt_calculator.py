import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO, TimeSequenceInputDTO
from core.calculator.dt.dt_calculator import DTCalculator
from core.calculator.dt.dt_input_dto import (
    DTGammaDTO, DTSampleDTO,
    DTDistributionInputDTO, DTShipmentTimeInputDTO
)
from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.dt.holiday.holiday_dto import HolidayResultDTO
from core.calculator.dt.holiday.holiday_calculator import HolidayCalculator


@patch("core.calculator.dt.dt_calculator.compute_gamma_mean")
@patch("core.calculator.dt.dt_calculator.compute_gamma_ci")
def test_calculate_gamma_distribution_without_holidays(mock_ci, mock_mean):
    mock_mean.return_value = 12.5
    mock_ci.return_value = (10.0, 15.0)

    mock_holiday_calculator = Mock(spec=HolidayCalculator)
    mock_holiday_calculator.calculate.side_effect = [  # elapsed, remaining lower, remaining upper
        HolidayResultDTO(False, False, False, [], [], []),
        HolidayResultDTO(False, False, False, [], [], []),
        HolidayResultDTO(False, False, False, [], [], [])
    ]

    order_time = datetime(2023, 1, 1, tzinfo=timezone.utc)

    time_input = TimeSequenceInputDTO(
        order_time=order_time,
        event_time=order_time,
        estimation_time=order_time
    )

    calculator = DTCalculator(holiday_calculator=mock_holiday_calculator, confidence=0.8)
    input_dto = DTDistributionInputDTO(
        site_id=1,
        distribution=DTGammaDTO(shape=2.0, scale=5.0, loc=2.5)
    )

    result = calculator.calculate(input_dto, time_input)

    assert isinstance(result, DT_DTO)
    assert result.elapsed_time == 0.0
    assert result.elapsed_working_time == 0.0
    assert result.remaining_working_time_lower == 10.0
    assert result.remaining_working_time_upper == 15.0
    assert result.remaining_time_lower == 10.0
    assert result.remaining_time_upper == 15.0


def test_calculate_sample_distribution_without_holidays():
    mock_holiday_calculator = Mock(spec=HolidayCalculator)
    mock_holiday_calculator.calculate.side_effect = [
        HolidayResultDTO(False, False, False, [], [], []),
        HolidayResultDTO(False, False, False, [], [], []),
        HolidayResultDTO(False, False, False, [], [], [])
    ]

    order_time = datetime(2023, 1, 1, tzinfo=timezone.utc)

    time_input = TimeSequenceInputDTO(
        order_time=order_time,
        event_time=order_time,
        estimation_time=order_time
    )

    calculator = DTCalculator(holiday_calculator=mock_holiday_calculator, confidence=0.9)
    input_dto = DTDistributionInputDTO(
        site_id=1,
        distribution=DTSampleDTO(mean=7.0, x=[5.0, 6.0, 7.0, 8.0, 9.0])
    )

    with patch("core.calculator.dt.dt_calculator.compute_sample_ci", return_value=(6.0, 8.0)):
        result = calculator.calculate(input_dto, time_input)

    assert isinstance(result, DT_DTO)
    assert result.elapsed_time == 0.0
    assert result.elapsed_working_time == 0.0
    assert result.remaining_working_time_lower == 6.0
    assert result.remaining_working_time_upper == 8.0
    assert result.remaining_time_lower == 6.0
    assert result.remaining_time_upper == 8.0


def test_calculate_shipment_dt():
    mock_holiday_result = HolidayResultDTO(
        closure_holidays=[Mock(), Mock()],
        weekend_holidays=[Mock()],
        working_holidays=[Mock()],
        consider_closure_holidays=True,
        consider_working_holidays=True,
        consider_weekends_holidays=True,
    )

    mock_holiday_calculator = Mock(spec=HolidayCalculator)
    mock_holiday_calculator.calculate.return_value = mock_holiday_result
    mock_holiday_calculator.consider_closure_holidays = True
    mock_holiday_calculator.consider_working_holidays = True
    mock_holiday_calculator.consider_weekends_holidays = True

    calculator = DTCalculator(holiday_calculator=mock_holiday_calculator, confidence=0.95)

    order_time = datetime.now(timezone.utc) - timedelta(hours=50)
    shipment_time = order_time + timedelta(hours=24 * 4)
    estimation_time = shipment_time + timedelta(hours=1)

    time_input = TimeSequenceInputDTO(
        order_time=order_time,
        event_time=shipment_time,
        estimation_time=estimation_time
    )

    input_dto = DTShipmentTimeInputDTO(
        site_id=1,
        shipment_time=shipment_time
    )

    result = calculator.calculate(input_dto, time_input)

    expected_elapsed = (shipment_time - order_time).total_seconds() / 3600.0
    expected_working = expected_elapsed - 3 * 24.0

    assert isinstance(result, DT_DTO)
    assert result.elapsed_time == pytest.approx(expected_elapsed, abs=1e-6)
    assert result.elapsed_working_time == pytest.approx(expected_working, abs=1e-6)
    assert result.remaining_time_lower == 0.0
    assert result.remaining_time_upper == 0.0
    assert result.remaining_working_time_lower == 0.0
    assert result.remaining_working_time_upper == 0.0
    assert result.remaining_holidays.n_closure_days == 0
    assert result.remaining_holidays.n_closure_days == 0


def test_invalid_input_raises():
    mock_holiday_calculator = Mock(spec=HolidayCalculator)
    calculator = DTCalculator(holiday_calculator=mock_holiday_calculator, confidence=0.9)

    class UnknownDTO:
        pass

    with pytest.raises(ValueError):
        calculator.calculate(UnknownDTO(), TimeSequenceInputDTO(                # type: ignore
            order_time=datetime.now(timezone.utc),
            event_time=datetime.now(timezone.utc) + timedelta(hours=1),
            estimation_time=datetime.now(timezone.utc) + timedelta(hours=2)
        ))


@patch("core.calculator.dt.dt_calculator.compute_gamma_mean")
@patch("core.calculator.dt.dt_calculator.compute_gamma_ci")
def test_gamma_distribution_with_holidays(mock_ci, mock_mean):
    mock_mean.return_value = 120.0
    mock_ci.return_value = (100.0, 140.0)

    order_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    event_time = order_time + timedelta(hours=96)
    estimation_time = event_time + timedelta(hours=1)

    time_input = TimeSequenceInputDTO(
        order_time=order_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    mock_holiday_calculator = Mock(spec=HolidayCalculator)
    mock_holiday_calculator.calculate.side_effect = [
        HolidayResultDTO(True, True, True, [Mock()], [Mock()], [Mock()]),
        HolidayResultDTO(True, True, True, [Mock()], [], []),
        HolidayResultDTO(True, True, True, [Mock()], [], [])
    ]

    calculator = DTCalculator(holiday_calculator=mock_holiday_calculator, confidence=0.95)
    input_dto = DTDistributionInputDTO(
        site_id=1,
        distribution=DTGammaDTO(shape=2.0, scale=4.0, loc=2.0)
    )

    result = calculator.calculate(input_dto, time_input)

    assert isinstance(result, DT_DTO)
    assert result.elapsed_time == 97.0
    assert result.elapsed_working_time == 97.0 - 2 * 24.0
    assert result.remaining_working_time_lower == 100.0 - result.elapsed_working_time
    assert result.remaining_working_time_upper == 140.0 - result.elapsed_working_time
    assert result.remaining_time_lower == result.remaining_working_time_lower + 1 * 24.0
    assert result.remaining_time_upper == result.remaining_working_time_upper + 1 * 24.0


def test_sample_distribution_with_holidays():
    order_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    event_time = order_time + timedelta(hours=96)
    estimation_time = event_time + timedelta(hours=1)

    time_input = TimeSequenceInputDTO(
        order_time=order_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    mock_holiday_calculator = Mock(spec=HolidayCalculator)
    mock_holiday_calculator.calculate.side_effect = [
        HolidayResultDTO(True, True, True, [Mock()], [Mock()], [Mock()]),
        HolidayResultDTO(True, True, True, [Mock()], [], []),
        HolidayResultDTO(True, True, True, [Mock()], [], [])
    ]

    calculator = DTCalculator(holiday_calculator=mock_holiday_calculator, confidence=0.95)
    input_dto = DTDistributionInputDTO(
        site_id=1,
        distribution=DTSampleDTO(mean=120.0, x=[144.0, 96.0, 120.0])
    )

    with patch("core.calculator.dt.dt_calculator.compute_sample_ci", return_value=(100.0, 140.0)):
        result = calculator.calculate(input_dto, time_input)

    assert isinstance(result, DT_DTO)
    assert result.elapsed_time == 97.0
    assert result.elapsed_working_time == 97.0 - 2 * 24.0
    assert result.remaining_working_time_lower == 100.0 - result.elapsed_working_time
    assert result.remaining_working_time_upper == 140.0 - result.elapsed_working_time
    assert result.remaining_time_lower == result.remaining_working_time_lower + 1 * 24.0
    assert result.remaining_time_upper == result.remaining_working_time_upper + 1 * 24.0
