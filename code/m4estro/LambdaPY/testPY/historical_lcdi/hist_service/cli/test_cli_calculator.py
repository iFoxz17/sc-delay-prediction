import pytest
import numpy as np
from hist_service.cli.cli_calculator import CLICalculator
from hist_service.cli.cli_dto import CLI_DTO

@pytest.fixture
def calculator():
    return CLICalculator()

def test_cli_with_zero_orders(calculator):
    result = calculator.calculate_cli(n_losses=0, n_orders=0)
    assert isinstance(result, CLI_DTO)
    assert np.isclose(result.value, 0.0)

def test_cli_with_nonzero_orders(calculator):
    result = calculator.calculate_cli(n_losses=3, n_orders=6)
    assert isinstance(result, CLI_DTO)
    assert np.isclose(result.value, 0.5)

def test_cli_with_no_rejections(calculator):
    result = calculator.calculate_cli(n_losses=0, n_orders=10)
    assert isinstance(result, CLI_DTO)
    assert np.isclose(result.value, 0.0)

def test_cli_with_float_inputs(calculator):
    result = calculator.calculate_cli(n_losses=2.5, n_orders=10.0)
    assert isinstance(result, CLI_DTO)
    assert np.isclose(result.value, 0.25)
