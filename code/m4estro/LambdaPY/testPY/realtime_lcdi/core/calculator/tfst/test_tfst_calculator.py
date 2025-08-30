import pytest
from unittest.mock import Mock, create_autospec, MagicMock

from model.alpha import AlphaType

from core.query_handler.params.params_result import PTParams

from core.calculator.tfst.tt.tt_dto import TT_DTO
from core.calculator.tfst.pt.pt_dto import PT_DTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO

from core.calculator.tfst.tfst_dto import TFSTCalculationDTO
from core.calculator.tfst.tfst_calculator import TFSTCalculator

def test_tfst_calculate_basic():
    pt = PT_DTO(lower=10.0, upper=20.0, n_paths=3, avg_wmi=0.5, avg_tmi=0.6, tmi_data=[], wmi_data=[], params=MagicMock(from_autospec=True))
    tt = TT_DTO(lower=30.0, upper=40.0, confidence=0.90)
    alpha = AlphaDTO(input=0.6, value=0.6, type_=AlphaType.CONST)

    calculator = TFSTCalculator()
    result = calculator.calculate(alpha=alpha, pt=pt, tt=tt)

    expected_lower = (1 - alpha.value) * pt.lower + alpha.value * tt.lower
    expected_upper = (1 - alpha.value) * pt.upper + alpha.value * tt.upper

    assert isinstance(result, TFSTCalculationDTO)
    assert result.lower == pytest.approx(expected_lower)
    assert result.upper == pytest.approx(expected_upper)
    assert result.alpha == alpha.value

def test_tfst_alpha_edge_cases():
    pt = PT_DTO(lower=5.0, upper=15.0, n_paths=3, avg_wmi=0.3, avg_tmi=0.4, tmi_data=[], wmi_data=[], params=MagicMock(from_autospec=True))
    tt = TT_DTO(lower=25.0, upper=35.0, confidence=0.9)
    
    calculator = TFSTCalculator()

    alpha = AlphaDTO(input=0.5, value=0.0, type_=AlphaType.CONST)
    # alpha = 0 means TFST == PT
    result_zero = calculator.calculate(alpha=alpha, pt=pt, tt=tt)
    assert result_zero.lower == pytest.approx(pt.lower)
    assert result_zero.upper == pytest.approx(pt.upper)
    assert result_zero.alpha == 0.0

    alpha = AlphaDTO(input=0.5, value=1.0, type_=AlphaType.EXP, maybe_tau=0.5, maybe_tt_weight=0.5) 
    # alpha = 1 means TFST == TT
    result_one = calculator.calculate(alpha=alpha, pt=pt, tt=tt)
    assert result_one.lower == pytest.approx(tt.lower)
    assert result_one.upper == pytest.approx(tt.upper)
    assert result_one.alpha == 1.0

def test_tfst_alpha_out_of_bounds():
    pt = PT_DTO(lower=5.0, upper=15.0, n_paths=1, avg_wmi=0.3, avg_tmi=0.4, tmi_data=[], wmi_data=[], params=MagicMock(from_autospec=True))
    tt = TT_DTO(lower=25.0, upper=35.0, confidence=0.9)

    calculator = TFSTCalculator()

    alpha = AlphaDTO(input=0.5, value=1.5, type_=AlphaType.MARKOV, maybe_tau=0.5, maybe_gamma=0.5)
    # Negative alpha (should still compute mathematically)
    result_neg = calculator.calculate(alpha=alpha, pt=pt, tt=tt)
    expected_lower_neg = -0.5 * pt.lower + 1.5 * tt.lower
    expected_upper_neg = -0.5 * pt.upper + 1.5 * tt.upper
    assert result_neg.lower == pytest.approx(expected_lower_neg)
    assert result_neg.upper == pytest.approx(expected_upper_neg)
    assert result_neg.alpha == 1.5

    alpha = AlphaDTO(input=0.5, value=-0.5, type_=AlphaType.CONST)
    # Alpha > 1 (should still compute mathematically)
    result_gt1 = calculator.calculate(alpha=alpha, pt=pt, tt=tt)
    expected_lower_gt1 = 1.5 * pt.lower + (-0.5) * tt.lower
    expected_upper_gt1 = 1.5 * pt.upper + (-0.5) * tt.upper
    assert result_gt1.lower == pytest.approx(expected_lower_gt1)
    assert result_gt1.upper == pytest.approx(expected_upper_gt1)
    assert result_gt1.alpha == -0.5
