from enum import Enum

from core.calculator.tfst.tt.tt_dto import TT_DTO
from core.calculator.tfst.pt.pt_dto import PT_DTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO

from core.calculator.tfst.tfst_dto import TFSTCalculationDTO

from logger import get_logger
logger = get_logger(__name__)

class TFSTCalculator:
    def __init__(self) -> None:
        pass

    def calculate(self, alpha: AlphaDTO, pt: PT_DTO, tt: TT_DTO) -> TFSTCalculationDTO:
        alpha_value: float = alpha.value        
        tfst_lower: float = (1 - alpha_value) * pt.lower + alpha_value * tt.lower
        tfst_upper: float = (1 - alpha_value) * pt.upper + alpha_value * tt.upper

        return TFSTCalculationDTO(
            lower=tfst_lower,
            upper=tfst_upper,
            alpha=alpha_value
        )