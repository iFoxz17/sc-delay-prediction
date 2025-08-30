import pytest

from core.calculator.cfdi.cfdi_calculator import CFDICalculator
from core.calculator.tfst.tfst_dto import TFSTCalculationDTO
from core.calculator.est.est_dto import EST_DTO
from core.calculator.cfdi.cfdi_dto import CFDI_DTO

def test_cfdi_calculator_calculate():
    calculator = CFDICalculator()

    # Sample inputs
    tfst = TFSTCalculationDTO(lower=15.0, upper=25.0, alpha=0.6)
    est = EST_DTO(value=20.0)

    result = calculator.calculate(tfst, est)

    expected_lower = 20.0 - 15.0
    expected_upper = 25.0 - 20.0

    assert isinstance(result, CFDI_DTO)
    assert result.lower == pytest.approx(expected_lower)
    assert result.upper == pytest.approx(expected_upper)
