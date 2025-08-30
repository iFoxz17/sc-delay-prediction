from typing import override

from model.alpha import AlphaType

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.tfst.alpha.alpha_calculator import AlphaCalculator
from core.calculator.tfst.alpha.alpha_input_dto import AlphaInputDTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO

from logger import get_logger
logger = get_logger(__name__)

class AlphaConstCalculator(AlphaCalculator):
    def __init__(self, alpha: float) -> None:
        self.alpha: float = alpha

    @override
    def calculate(self, alpha_input_dto: AlphaInputDTO, time_sequence: TimeSequenceDTO) -> AlphaDTO:
        return AlphaDTO(
            input=self.alpha,
            value=self.alpha,
            type_=AlphaType.CONST,
        )