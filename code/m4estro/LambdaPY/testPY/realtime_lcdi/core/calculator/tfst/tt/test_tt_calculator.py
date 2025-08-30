import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.tfst.tt.tt_calculator import TTCalculator
from core.calculator.tfst.tt.tt_input_dto import (
    TTInputDTO, TTGammaDTO, TTSampleDTO
)
from core.calculator.tfst.tt.tt_dto import TT_DTO

@pytest.fixture
def time_sequence() -> TimeSequenceDTO:
    order_time = datetime(2025, 6, 21, 10, tzinfo=timezone.utc)
    shipment_time = order_time + timedelta(hours=2)
    event_time = shipment_time + timedelta(hours=3)
    estimation_time = event_time + timedelta(hours=2)
    
    return TimeSequenceDTO(
        order_time=order_time,
        shipment_time=shipment_time,
        event_time=event_time,
        estimation_time=estimation_time
    )


@patch("core.calculator.tfst.tt.tt_calculator.compute_gamma_ci")
def test_calculate_with_gamma_input(mock_gamma_ci, time_sequence):
    mock_gamma_ci.return_value = (30.0, 50.0)

    gamma_dto = TTGammaDTO(shape=2.0, scale=3.0, loc=0.0)
    input_dto = TTInputDTO(distribution=gamma_dto)

    calculator = TTCalculator(confidence=0.95)
    result = calculator.calculate(input_dto, time_sequence)

    expected_lower = 30.0 - 5.0
    expected_upper = 50.0 - 5.0

    assert isinstance(result, TT_DTO)
    assert result.lower == pytest.approx(expected_lower)
    assert result.upper == pytest.approx(expected_upper)
    assert result.confidence == 0.95

    mock_gamma_ci.assert_called_once_with(shape=2.0, scale=3.0, loc=0.0, confidence_level=0.95)

@patch("core.calculator.tfst.tt.tt_calculator.compute_gamma_ci")
def test_gamma_ci_with_elapsed_time_greater_than_bounds(mock_gamma_ci, time_sequence):
    mock_gamma_ci.return_value = (2.0, 4.0)  # very small CI

    gamma_dto = TTGammaDTO(shape=1.0, scale=1.0, loc=0.0)
    input_dto = TTInputDTO(distribution=gamma_dto)

    calculator = TTCalculator(confidence=0.95)
    result = calculator.calculate(input_dto, time_sequence)

    assert result.lower == 0.0
    assert result.upper == 0.0
    assert result.confidence == 0.95

@patch("core.calculator.tfst.tt.tt_calculator.compute_gamma_ci")
def test_gamma_ci_with_elapsed_time_greater_than_lower_only(mock_gamma_ci, time_sequence):
    mock_gamma_ci.return_value = (4.0, 12.0)  # elapsed = 5h

    gamma_dto = TTGammaDTO(shape=1.0, scale=1.0, loc=0.0)
    input_dto = TTInputDTO(distribution=gamma_dto)

    calculator = TTCalculator(confidence=0.95)
    result = calculator.calculate(input_dto, time_sequence)

    assert result.lower == 0.0
    assert result.upper == pytest.approx(7.0)
    assert result.confidence == 0.95


@patch("core.calculator.tfst.tt.tt_calculator.compute_sample_ci")
def test_calculate_with_sample_input(mock_sample_ci, time_sequence):
    mock_sample_ci.return_value = (20.0, 40.0)

    sample_dto = TTSampleDTO(x=[10.0, 20.0, 30.0, 40.0], mean=30.0)
    input_dto = TTInputDTO(distribution=sample_dto)

    calculator = TTCalculator(confidence=0.9)
    result = calculator.calculate(input_dto, time_sequence)

    expected_lower = 20.0 - 5.0
    expected_upper = 40.0 - 5.0

    assert result.lower == pytest.approx(expected_lower)
    assert result.upper == pytest.approx(expected_upper)
    assert result.confidence == 0.9

    mock_sample_ci.assert_called_once_with(x=sample_dto.x, confidence_level=0.9)

@patch("core.calculator.tfst.tt.tt_calculator.compute_sample_ci")
def test_sample_ci_with_elapsed_time_greater_than_bounds(mock_sample_ci, time_sequence):
    mock_sample_ci.return_value = (1.0, 3.0)  # small interval

    sample_dto = TTSampleDTO(x=[1.0, 2.0, 3.0], mean=2.0)
    input_dto = TTInputDTO(distribution=sample_dto)

    calculator = TTCalculator(confidence=0.85)
    result = calculator.calculate(input_dto, time_sequence)

    assert result.lower == 0.0
    assert result.upper == 0.0
    assert result.confidence == 0.85


def test_unsupported_input_type_raises(time_sequence):
    class UnsupportedInput:
        pass

    unsupported = UnsupportedInput()
    input_dto = TTInputDTO(distribution=unsupported)  # type: ignore

    calculator = TTCalculator(confidence=0.8)
    with pytest.raises(ValueError, match="Unsupported TTInputDTO type"):
        calculator.calculate(input_dto, time_sequence)
