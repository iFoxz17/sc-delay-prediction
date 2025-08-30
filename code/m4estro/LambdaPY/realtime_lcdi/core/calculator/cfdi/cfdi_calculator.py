from typing import Tuple

from core.calculator.tfst.tfst_dto import TFSTCalculationDTO
from core.calculator.est.est_dto import EST_DTO

from core.calculator.cfdi.cfdi_dto import CFDI_DTO

from logger import get_logger
logger = get_logger(__name__)

class CFDICalculator:
    def __init__(self) -> None:
        pass

    def calculate(self, tfst: TFSTCalculationDTO, est: EST_DTO) -> CFDI_DTO:
        est_value: float = est.value

        cfdi_lower: float = est_value - tfst.lower
        cfdi_upper: float = tfst.upper - est_value

        return CFDI_DTO(
            lower=cfdi_lower,
            upper=cfdi_upper,
        )