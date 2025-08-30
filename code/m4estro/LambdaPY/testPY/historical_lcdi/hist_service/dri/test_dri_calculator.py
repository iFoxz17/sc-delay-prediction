import pytest
import numpy as np
from hist_service.dri.dri_calculator import DRICalculator
from hist_service.dri.dri_dto import DRI_DTO

@pytest.fixture
def calculator():
    return DRICalculator()

def test_dri_with_zero_orders(calculator):
    result = calculator.calculate_dri(n_rejections=0, n_orders=0)
    assert isinstance(result, DRI_DTO)
    assert np.isclose(result.value, 0.0)

def test_dri_with_nonzero_orders(calculator):
    result = calculator.calculate_dri(n_rejections=3, n_orders=6)
    assert isinstance(result, DRI_DTO)
    assert np.isclose(result.value, 0.5)

def test_dri_with_no_rejections(calculator):
    result = calculator.calculate_dri(n_rejections=0, n_orders=10)
    assert isinstance(result, DRI_DTO)
    assert np.isclose(result.value, 0.0)

def test_dri_with_float_inputs(calculator):
    result = calculator.calculate_dri(n_rejections=2.5, n_orders=10.0)
    assert isinstance(result, DRI_DTO)
    assert np.isclose(result.value, 0.25)
