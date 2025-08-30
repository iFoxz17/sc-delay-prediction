from typing import override
from stats_utils import compute_gamma_mean

from model.alpha import AlphaType

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO, EstimationStage

from core.calculator.tfst.alpha.alpha_calculator import AlphaCalculator
from core.calculator.tfst.alpha.alpha_input_dto import AlphaInputDTO, AlphaDistributionDTO, AlphaGammaDTO, AlphaSampleDTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO

from logger import get_logger
logger = get_logger(__name__)

class AlphaExpCalculator(AlphaCalculator):
    def __init__(self, tt_weight: float) -> None:
        self.tt_weight: float = tt_weight

    def _exp(self, tau: float) -> float:
        if self.tt_weight == 0:
            return 0.0
        if tau == 1 and self.tt_weight == 1:        # handle 0 ** 0 case
            return 1.0
        
        return (1 - tau) ** (1 / self.tt_weight - 1)
    
    def _calculate_distribution_ast(self, alpha_distribution: AlphaDistributionDTO) -> float:
        mean: float
        
        if isinstance(alpha_distribution, AlphaGammaDTO):
            alpha_gamma: AlphaGammaDTO = alpha_distribution
            mean: float = compute_gamma_mean(
                shape=alpha_gamma.shape, 
                scale=alpha_gamma.scale,
                loc=alpha_gamma.loc
            )
            logger.debug(f"Computed AST from gamma distribution for alpha calculation: {mean}")
        elif isinstance(alpha_distribution, AlphaSampleDTO):
            alpha_sample: AlphaSampleDTO = alpha_distribution
            mean: float = alpha_sample.mean
            logger.debug(f"Computed AST from sample distribution for alpha calculation: {mean}")
        else:
            logger.error(f"Unsupported Alpha distribution type: {type(alpha_distribution)}. This should never happen.")
            raise ValueError(f"Unsupported Alpha distribution type: {type(alpha_distribution)}. This should never happen.")
        
        return mean

    @override
    def calculate(self, alpha_input_dto: AlphaInputDTO, time_sequence: TimeSequenceDTO) -> AlphaDTO:
        if time_sequence.get_estimation_stage() == EstimationStage.DISPATCH:
            logger.debug(f"Estimation performed in {EstimationStage.DISPATCH.value} stage: returning alpha = 1.0")
            return AlphaDTO(
                input=1.0,
                value=1.0,
                type_=AlphaType.EXP,
                maybe_tt_weight=self.tt_weight,
                maybe_tau=0.0,
            )
        
        elapsed_time: float = (time_sequence.shipment_estimation_time - time_sequence.shipment_time).total_seconds() / 3600
        ast: float = self._calculate_distribution_ast(alpha_input_dto.st_distribution)
        tau: float = min(1, elapsed_time / ast)
        alpha_value: float = self._exp(tau)

        return AlphaDTO(
            input=tau,
            value=alpha_value,
            type_=AlphaType.EXP,
            maybe_tt_weight=self.tt_weight,
            maybe_tau=tau,
        )