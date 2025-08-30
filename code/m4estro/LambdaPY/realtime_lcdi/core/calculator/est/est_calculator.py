from core.calculator.est.est_dto import EST_DTO
from core.calculator.tfst.tfst_dto import TFSTCalculationDTO

from logger import get_logger
logger = get_logger(__name__)

class ESTCalculator:
    def __init__(self) -> None:
        pass

    def calculate(self, tfst: TFSTCalculationDTO) -> EST_DTO:
        est: float = (tfst.lower + tfst.upper) / 2.0
        
        return EST_DTO(value=est)