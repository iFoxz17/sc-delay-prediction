from typing import override

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.tfst.alpha.alpha_calculator import AlphaCalculator
from core.calculator.tfst.alpha.alpha_input_dto import AlphaInputDTO, AlphaDistributionDTO, AlphaGammaDTO, AlphaSampleDTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO

from logger import get_logger
logger = get_logger(__name__)

class AlphaMarkovCalculator(AlphaCalculator):
    def __init__(self) -> None:
        pass

    @override
    def calculate(self, alpha_input_dto: AlphaInputDTO, time_sequence: TimeSequenceDTO) -> AlphaDTO:
        if alpha_input_dto.vertex_id is None:
            logger.error("Vertex ID must be provided for Markov alpha calculation.")
            raise ValueError("Vertex ID must be provided for Markov alpha calculation.")

        raise NotImplementedError("Not implemented yet")