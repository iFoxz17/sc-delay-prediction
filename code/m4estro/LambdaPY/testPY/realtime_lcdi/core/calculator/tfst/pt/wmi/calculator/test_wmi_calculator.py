import pytest
from core.calculator.tfst.pt.wmi.calculator.wmi_calculator import WMICalculator
from core.calculator.tfst.pt.wmi.calculator.wmi_calculation_input_dto import WMICalculationInputDTO
from core.calculator.tfst.pt.wmi.calculator.wmi_calculation_dto import By

# --- Fixtures ---

@pytest.fixture
def calculator():
    return WMICalculator()

# --- Tests ---

def test_empty_weather_and_temp(calculator):
    dto = WMICalculationInputDTO(weather_codes=[], temperature_celsius=[])
    result = calculator.calculate(dto)
    
    assert result.value == 0.0
    assert result.weather_code == ""
    assert result.weather_description == ""
    assert result.temperature_celsius == 0.0

def test_single_weather_code(calculator):
    dto = WMICalculationInputDTO(weather_codes=["type_13"], temperature_celsius=[-5])
    result = calculator.calculate(dto)

    # Type 13 has score 1.0, very high
    assert result.value == pytest.approx(1.0)
    assert result.weather_code == "type_13"
    assert result.weather_description == "Heavy Freezing Rain"
    assert result.by == By.WEATHER_CONDITION

def test_single_temperature_score_wins(calculator):
    high_temp = 100.0  # Should yield a temp score very close to 1
    dto = WMICalculationInputDTO(weather_codes=["type_2"], temperature_celsius=[high_temp])
    result = calculator.calculate(dto)

    assert result.by == By.TEMPERATURE
    assert result.temperature_celsius == high_temp
    assert result.value == pytest.approx(1.0, rel=1e-2)

def test_multiple_weather_codes(calculator):
    dto = WMICalculationInputDTO(weather_codes=["type_2", "type_13", "type_4"], temperature_celsius=[0.0])
    result = calculator.calculate(dto)

    # type_13 has the highest score (1.0)
    assert result.weather_code == "type_13"
    assert result.weather_description == "Heavy Freezing Rain"
    assert result.value == pytest.approx(1.0)
    assert result.by == By.WEATHER_CONDITION

def test_multiple_temperatures(calculator):
    dto = WMICalculationInputDTO(weather_codes=[], temperature_celsius=[-10, 20, 50])
    result = calculator.calculate(dto)

    # High temp should give highest score
    assert result.temperature_celsius == 50
    assert result.by == By.TEMPERATURE

def test_invalid_weather_code_ignored(calculator):
    dto = WMICalculationInputDTO(weather_codes=["invalid_code", "type_14"], temperature_celsius=[0.0])
    result = calculator.calculate(dto)

    assert result.weather_code == "type_14"
    assert result.weather_description == "Light Freezing Rain"
    assert result.value > 0.0
    assert result.by == By.WEATHER_CONDITION
