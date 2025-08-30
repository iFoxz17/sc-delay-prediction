import pytest
from core.calculator.tfst.pt.vertex_time.vertex_time_calculator import VertexTimeCalculator
from core.calculator.tfst.pt.vertex_time.vertex_time_input_dto import VertexTimeInputDTO
from core.calculator.tfst.pt.vertex_time.vertex_time_dto import VertexTimeDTO

@pytest.fixture
def calculator():
    return VertexTimeCalculator()

def test_calculate_returns_avg_ori(calculator):
    dto = VertexTimeInputDTO(avg_ori=12.34)

    result: VertexTimeDTO = calculator.calculate(dto, confidence=0.8)

    assert result.lower == 12.34
    assert result.upper == 12.34
    
