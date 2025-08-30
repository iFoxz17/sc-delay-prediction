import pytest
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO, TimeSequenceInputDTO
from core.calculator.tfst.alpha.alpha_exp_calculator import AlphaExpCalculator
from core.calculator.tfst.alpha.alpha_input_dto import AlphaGammaDTO, AlphaSampleDTO, AlphaInputDTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO


@patch("core.calculator.tfst.alpha.alpha_exp_calculator.compute_gamma_mean")
def test_calculate_with_gamma_distribution(mock_compute_gamma_mean):
    calculator = AlphaExpCalculator(tt_weight=0.5)
    
    order_time = datetime(2025, 6, 21, 10, tzinfo=timezone.utc)
    shipment_time = order_time + timedelta(hours=2)
    event_time = shipment_time + timedelta(hours=1)
    estimation_time = event_time + timedelta(hours=1)

    time_sequence: TimeSequenceDTO = TimeSequenceDTO(
        order_time=order_time,
        shipment_time=shipment_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    gamma_dto = AlphaGammaDTO(shape=2.0, scale=1.0, loc=0.0)
    mock_compute_gamma_mean.return_value = 4.0

    input_dto = AlphaInputDTO(st_distribution=gamma_dto)

    result = calculator.calculate(input_dto, time_sequence)

    assert isinstance(result, AlphaDTO)
    assert result.input == 0.5
    assert result.value == 0.5


def test_calculate_with_sample_distribution():
    calculator = AlphaExpCalculator(tt_weight=0.5)

    order_time = datetime(2025, 6, 21, 10, tzinfo=timezone.utc)
    shipment_time = order_time + timedelta(hours=3)
    event_time = shipment_time + timedelta(hours=1)
    estimation_time = event_time + timedelta(hours=1)

    time_sequence = TimeSequenceDTO(
        order_time=order_time,
        shipment_time=shipment_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    sample_dto = AlphaSampleDTO(mean=4.0)
    input_dto = AlphaInputDTO(st_distribution=sample_dto, vertex_id=1)

    result = calculator.calculate(input_dto, time_sequence)

    assert isinstance(result, AlphaDTO)
    assert result.input == 0.5
    assert result.value == 0.5


def test_calculate_with_invalid_distribution_type():
    class InvalidDTO:
        pass

    calculator = AlphaExpCalculator(tt_weight=0.5)

    order_time = datetime(2025, 6, 21, 10, tzinfo=timezone.utc)
    shipment_time = order_time + timedelta(hours=2)
    event_time = shipment_time + timedelta(hours=1)
    estimation_time = event_time + timedelta(hours=1)

    time_sequence = TimeSequenceDTO(
        order_time=order_time,
        shipment_time=shipment_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    input_dto = AlphaInputDTO(st_distribution=InvalidDTO())     # type: ignore

    with pytest.raises(ValueError):
        calculator.calculate(input_dto, time_sequence)


def test_exp_method():
    calculator = AlphaExpCalculator(tt_weight=0.5)

    # q = 1/tt_weight - 1 = 1
    # _exp(0) = (1-0)^1 = 1
    assert calculator._exp(0) == 1.0

    # _exp(0.5) = (1-0.5)^1 = 0.5
    assert calculator._exp(0.5) == 0.5

    # _exp(1) = (1-1)^1 = 0
    assert calculator._exp(1) == 0.0

    for tao in np.linspace(0, 1, 100):
        expected = (1 - tao) ** (1 / calculator.tt_weight - 1)
        actual = calculator._exp(tao)
        assert actual == pytest.approx(expected, rel=1e-5)
        assert 0 <= actual <= 1, "Alpha value should be between 0 and 1"


@patch("core.calculator.tfst.alpha.alpha_exp_calculator.compute_gamma_mean")
def test_calculate_distribution_ast_gamma(mock_compute_gamma_mean):
    mock_compute_gamma_mean.return_value = 5.0
    calculator = AlphaExpCalculator(tt_weight=0.5)
    gamma_dto = AlphaGammaDTO(shape=2.0, scale=1.0, loc=0.0)

    mean = calculator._calculate_distribution_ast(gamma_dto)
    assert mean == 5.0
    mock_compute_gamma_mean.assert_called_once_with(shape=2.0, scale=1.0, loc=0.0)


def test_calculate_distribution_ast_sample():
    calculator = AlphaExpCalculator(tt_weight=0.5)
    sample_dto = AlphaSampleDTO(mean=3.3)

    mean = calculator._calculate_distribution_ast(sample_dto)
    assert mean == 3.3


def test_calculate_distribution_ast_invalid():
    calculator = AlphaExpCalculator(tt_weight=0.5)

    class InvalidDTO:
        pass

    with pytest.raises(ValueError):
        calculator._calculate_distribution_ast(InvalidDTO())        # type: ignore
