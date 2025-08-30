import pytest
from core.calculator.est.est_calculator import ESTCalculator
from core.calculator.tfst.tfst_dto import TFSTCalculationDTO
from core.calculator.est.est_dto import EST_DTO

def test_est_calculator_calculate():
    calculator = ESTCalculator()
    tfst = TFSTCalculationDTO(lower=10.0, upper=20.0, alpha=0.5)

    result = calculator.calculate(tfst)

    expected_value = (10.0 + 20.0) / 2.0
    assert isinstance(result, EST_DTO)
    assert result.value == pytest.approx(expected_value)
