from typing import Tuple, Union
from datetime import datetime

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.tfst.tt.tt_dto import TT_DTO
from core.calculator.tfst.tt.tt_input_dto import TTInputDTO, TTGammaDTO, TTSampleDTO

from stats_utils import compute_gamma_ci, compute_sample_ci

from logger import get_logger
logger = get_logger(__name__)

class TTCalculator:
    def __init__(self, confidence: float) -> None:
        self.confidence: float = confidence

    def _calculate_tt(self, l: float, u: float, starting_time: datetime, estimation_time: datetime) -> Tuple[float, float]:
        elapsed_hours: float = (estimation_time - starting_time).total_seconds() / 3600.0

        tt_lower: float = max(l - elapsed_hours, 0.0)
        tt_upper: float = max(u - elapsed_hours, 0.0)

        return tt_lower, tt_upper

    def _calculate_gamma_tt(self, tt_gamma_input: TTGammaDTO, starting_time: datetime, estimation_time: datetime) -> Tuple[float, float]:
        l, u = compute_gamma_ci(
            shape=tt_gamma_input.shape,
            scale=tt_gamma_input.scale,
            loc=tt_gamma_input.loc,
            confidence_level=self.confidence
        )
        logger.debug(f"Gamma TT CI computed: lower={l}, upper={u}")

        return self._calculate_tt(l, u, starting_time, estimation_time)
    
    def _calculate_sample_tt(self, tt_sample_input: TTSampleDTO, starting_time: datetime, estimation_time: datetime) -> Tuple[float, float]:
        l, u = compute_sample_ci(x=tt_sample_input.x, confidence_level=self.confidence)
        logger.debug(f"Sample TT CI computed: lower={l}, upper={u}")

        return self._calculate_tt(l, u, starting_time, estimation_time)

    def calculate(self, tt_input: TTInputDTO, time_sequence: TimeSequenceDTO) -> TT_DTO:
        tt_distribution: Union[TTGammaDTO, TTSampleDTO] = tt_input.distribution
        shipment_time: datetime = time_sequence.shipment_time
        estimation_time: datetime = time_sequence.shipment_estimation_time
        confidence: float = self.confidence

        if isinstance(tt_distribution, TTGammaDTO):
            remaining_l, remaining_u = self._calculate_gamma_tt(tt_distribution, shipment_time, estimation_time)
        elif isinstance(tt_distribution, TTSampleDTO):
            remaining_l, remaining_u = self._calculate_sample_tt(tt_distribution, shipment_time, estimation_time)
        else:
            logger.error(f"Unsupported TTInputDTO type: {type(tt_distribution)}. This should never happen.")
            raise ValueError(f"Unsupported TTInputDTO type: {type(tt_distribution)}. This should never happen.")

        elapsed: float = (estimation_time - shipment_time).total_seconds() / 3600.0
        total_l: float = elapsed + remaining_l
        total_u: float = elapsed + remaining_u

        logger.debug(f"TT computed with confidence {confidence}: " 
                     f"total_time=[{total_l}, {total_u}], "
                     f"elapsed_time={elapsed}, "
                     f"remaining_time=[{remaining_l}, {remaining_u}]")

        return TT_DTO(
            lower=remaining_l,
            upper=remaining_u,
            confidence=confidence
        )
    
    def empty(self) -> TT_DTO:
        return TT_DTO(
            lower=0.0,
            upper=0.0,
            confidence=self.confidence
        )
