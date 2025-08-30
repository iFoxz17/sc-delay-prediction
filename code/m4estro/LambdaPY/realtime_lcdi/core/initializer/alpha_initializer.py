from model.alpha import AlphaType

from core.calculator.tfst.alpha.alpha_calculator import AlphaCalculator
from core.calculator.tfst.alpha.alpha_const_calculator import AlphaConstCalculator
from core.calculator.tfst.alpha.alpha_exp_calculator import AlphaExpCalculator
from core.calculator.tfst.alpha.alpha_markov_calculator import AlphaMarkovCalculator

from logger import get_logger
logger = get_logger(__name__)
    
class AlphaInitializer:
    def __init__(self, alpha_const_value: float, alpha_exp_tt_weight: float) -> None:
        self.alpha_const_value: float = alpha_const_value
        self.alpha_exp_tt_weight: float = alpha_exp_tt_weight
        
    def initialize(self, alpha_type: AlphaType) -> AlphaCalculator:
        match alpha_type:
            case AlphaType.CONST:
                logger.debug(f"Initializing AlphaConstCalculator with value: {self.alpha_const_value}")
                return AlphaConstCalculator(alpha=self.alpha_const_value)
            case AlphaType.EXP:
                logger.debug(f"Initializing AlphaExpCalculator with tt_weight: {self.alpha_exp_tt_weight}")
                return AlphaExpCalculator(tt_weight=self.alpha_exp_tt_weight)
            case AlphaType.MARKOV:
                logger.debug("Initializing AlphaMarkovCalculator")
                return AlphaMarkovCalculator()
            
        logger.error(f"Unsupported alpha calculator type: {alpha_type}. This should never happen.")
        raise ValueError(f"Unsupported alpha calculator type: {alpha_type}. This should never happen.")