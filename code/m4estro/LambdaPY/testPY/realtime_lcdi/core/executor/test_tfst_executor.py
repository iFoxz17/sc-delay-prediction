import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from model.alpha import AlphaType

from core.executor.tfst_executor import TFSTExecutor, TFSTExecutorResult, TFSTCompute

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

# Alpha
from core.calculator.tfst.alpha.alpha_input_dto import AlphaInputDTO, AlphaGammaDTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO

# PT
from core.calculator.tfst.pt.pt_input_dto import PTInputDTO
from core.calculator.tfst.pt.pt_dto import PT_DTO

# TT
from core.calculator.tfst.tt.tt_input_dto import TTInputDTO, TTGammaDTO
from core.calculator.tfst.tt.tt_dto import TT_DTO

# TFST
from core.calculator.tfst.tfst_dto import TFST_DTO

@pytest.fixture
def time_sequence():
    return TimeSequenceDTO(
        order_time=datetime(2025, 6, 21, 10, tzinfo=timezone.utc),
        shipment_time=datetime(2025, 6, 21, 12, tzinfo=timezone.utc),
        event_time=datetime(2025, 6, 21, 13, tzinfo=timezone.utc),
        estimation_time=datetime(2025, 6, 21, 14, tzinfo=timezone.utc)
    )

@pytest.fixture
def input_dtos():
    alpha_input = AlphaInputDTO(
        st_distribution=AlphaGammaDTO(shape=2.0, scale=1.5, loc=0.0),
    )

    pt_input = PTInputDTO(
        vertex_id=101,
        carrier_names=["CarrierX", "CarrierY"],
    )

    tt_input = TTInputDTO(
        distribution=TTGammaDTO(shape=1.8, scale=2.5, loc=0.0),
    )

    return alpha_input, pt_input, tt_input


@pytest.fixture
def mocked_calculators():
    alpha_calculator = MagicMock()
    pt_calculator = MagicMock()
    tt_calculator = MagicMock()
    tfst_calculator = MagicMock()

    alpha_dto = AlphaDTO(input=0.5, value=0.8, type_=AlphaType.CONST)
    pt_dto = PT_DTO(lower=1.0, upper=2.0, 
                    n_paths=5, avg_wmi=0.4, avg_tmi=0.5, 
                    tmi_data=[], wmi_data=[], params=MagicMock(from_autospec=True))
    tt_dto = TT_DTO(lower=2.0, upper=3.5, confidence=0.95)
    tfst_dto = TFST_DTO(lower=3.0, upper=5.5, alpha=0.8, tolerance=0.1, computed=TFSTCompute.ALL)

    alpha_calculator.calculate.return_value = alpha_dto
    pt_calculator.calculate.return_value = pt_dto
    tt_calculator.calculate.return_value = tt_dto
    tfst_calculator.calculate.return_value = tfst_dto

    return alpha_calculator, pt_calculator, tt_calculator, tfst_calculator, alpha_dto, pt_dto, tt_dto, tfst_dto


def assert_result_matches(result, alpha, pt, tt, tfst):
    assert isinstance(result, TFSTExecutorResult)
    assert result.alpha == alpha
    assert result.pt == pt
    assert result.tt == tt
    assert result.tfst == tfst


def test_tfst_executor_sequential(input_dtos, time_sequence, mocked_calculators):
    alpha_calc, pt_calc, tt_calc, tfst_calc, alpha, pt, tt, tfst = mocked_calculators
    executor = TFSTExecutor(
        alpha_calculator=alpha_calc,
        pt_calculator=pt_calc,
        tt_calculator=tt_calc,
        tfst_calculator=tfst_calc,
        parallelization=0,
        tolerance=0.1
    )

    result = executor.execute(time_sequence, *input_dtos)

    alpha_calc.calculate.assert_called_once_with(input_dtos[0], time_sequence)
    pt_calc.calculate.assert_called_once_with(input_dtos[1], time_sequence)
    tt_calc.calculate.assert_called_once_with(input_dtos[2], time_sequence)
    tfst_calc.calculate.assert_called_once_with(alpha=alpha, pt=pt, tt=tt)

    assert_result_matches(result, alpha, pt, tt, tfst)


def test_tfst_executor_parallel(input_dtos, time_sequence, mocked_calculators):
    alpha_calc, pt_calc, tt_calc, tfst_calc, alpha, pt, tt, tfst = mocked_calculators
    executor = TFSTExecutor(
        alpha_calculator=alpha_calc,
        pt_calculator=pt_calc,
        tt_calculator=tt_calc,
        tfst_calculator=tfst_calc,
        parallelization=4,
        tolerance=0.1
    )

    result = executor.execute(time_sequence, *input_dtos)

    alpha_calc.calculate.assert_called_once_with(input_dtos[0], time_sequence)
    pt_calc.calculate.assert_called_once_with(input_dtos[1], time_sequence)
    tt_calc.calculate.assert_called_once_with(input_dtos[2], time_sequence)
    tfst_calc.calculate.assert_called_once_with(alpha=alpha, pt=pt, tt=tt)

    assert_result_matches(result, alpha, pt, tt, tfst)
