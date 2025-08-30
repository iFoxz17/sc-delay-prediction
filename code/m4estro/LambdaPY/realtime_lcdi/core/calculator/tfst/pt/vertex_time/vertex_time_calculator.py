from core.calculator.tfst.pt.vertex_time.vertex_time_input_dto import VertexTimeInputDTO 
from core.calculator.tfst.pt.vertex_time.vertex_time_dto import VertexTimeDTO

class VertexTimeCalculator:
    def __init__(self) -> None:
        pass

    def calculate(self, ori_dto: VertexTimeInputDTO, confidence: float) -> VertexTimeDTO:
        return VertexTimeDTO(
            lower=ori_dto.avg_ori,
            upper=ori_dto.avg_ori
        )