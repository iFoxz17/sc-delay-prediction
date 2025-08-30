from abc import ABC, abstractmethod

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.tfst.alpha.alpha_input_dto import AlphaInputDTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO

class AlphaCalculator(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def calculate(self, alpha_input_dto: AlphaInputDTO, time_sequence: TimeSequenceDTO) -> AlphaDTO:
        pass