from typing import Dict, Any
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.tfst.pt.pt_calculator import PTCalculator
from core.calculator.tfst.pt.pt_input_dto import PTInputDTO
from core.calculator.tfst.pt.pt_dto import PT_DTO

from core.calculator.tfst.tt.tt_calculator import TTCalculator
from core.calculator.tfst.tt.tt_input_dto import TTInputDTO
from core.calculator.tfst.tt.tt_dto import TT_DTO

from core.calculator.tfst.alpha.alpha_calculator import AlphaCalculator
from core.calculator.tfst.alpha.alpha_input_dto import AlphaInputDTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO

from core.calculator.tfst.tfst_calculator import TFSTCalculator
from core.calculator.tfst.tfst_dto import TFST_DTO, TFSTCalculationDTO

from logger import get_logger
logger = get_logger(__name__)

class TFSTCompute(Enum):
    PT = "pt"
    TT = "tt"
    ALL = "all"

@dataclass
class TFSTExecutorResult:
    alpha: AlphaDTO
    pt: PT_DTO
    tt: TT_DTO
    tfst: TFST_DTO

class TFSTExecutor:
    def __init__(self,
                 alpha_calculator: AlphaCalculator,
                 pt_calculator: PTCalculator,
                 tt_calculator: TTCalculator,
                 tfst_calculator: TFSTCalculator,
                 parallelization: int,
                 tolerance: float
                 ) -> None:
        
        self.alpha_calculator: AlphaCalculator = alpha_calculator
        self.pt_calculator: PTCalculator = pt_calculator
        self.tt_calculator: TTCalculator = tt_calculator
        self.tfst_calculator: TFSTCalculator = tfst_calculator
        
        self.parallelization: int = parallelization
        self.tolerance: float = tolerance

    def _optimize_by_alpha(self, alpha: AlphaDTO) -> TFSTCompute: 
        tolerance: float = self.tolerance
        if alpha.value < tolerance:
            logger.debug(f"Alpha = {alpha.value} < {tolerance} = tolerance: TT weight is negligible")
            return TFSTCompute.PT
        
        if alpha.value > 1 - tolerance:
            logger.debug(f"Alpha = {alpha.value} > {1 - tolerance} = 1 - tolerance: PT weight is negligible") 
            return TFSTCompute.TT
        
        return TFSTCompute.ALL
        
    def execute(self,
                time_sequence: TimeSequenceDTO,
                alpha_input: AlphaInputDTO,
                pt_input: PTInputDTO,
                tt_input: TTInputDTO,
                ) -> TFSTExecutorResult:
        
        alpha: AlphaDTO = self.alpha_calculator.calculate(alpha_input, time_sequence)
        logger.debug(f"Alpha calculated successfully: {alpha}")
      
        if self.parallelization > 0:
            logger.debug("Starting TFST calculation in parallel mode")
            return self._execute_parallel(time_sequence, alpha, pt_input, tt_input)

        logger.debug("Starting TFST calculation in sequential mode")
        return self._execute_sequential(time_sequence, alpha, pt_input, tt_input)
    
    def _execute_parallel(self,
                          time_sequence: TimeSequenceDTO,
                          alpha: AlphaDTO,
                          pt_input: PTInputDTO,
                          tt_input: TTInputDTO
                          ) -> TFSTExecutorResult:

        with ThreadPoolExecutor() as executor:
            to_compute: TFSTCompute = self._optimize_by_alpha(alpha)

            try:
                futures: Dict[str, Any] = {}
                if to_compute == TFSTCompute.PT or to_compute == TFSTCompute.ALL:
                    logger.debug("Submitting PT calculation to executor")
                    futures['pt'] = executor.submit(self.pt_calculator.calculate, pt_input, time_sequence)
                else:
                    logger.debug("Skipping PT calculation due to negligible weight")
                    futures['pt'] = executor.submit(self.pt_calculator.empty_path_dto)

                if to_compute == TFSTCompute.TT or to_compute == TFSTCompute.ALL:
                    logger.debug("Submitting TT calculation to executor")
                    futures['tt'] = executor.submit(self.tt_calculator.calculate, tt_input, time_sequence)
                else:
                    logger.debug("Skipping TT calculation due to negligible weight")
                    futures['tt'] = executor.submit(self.tt_calculator.empty)
            except Exception:
                logger.exception("Error during parallel calculation setup")
                raise

            tt: TT_DTO = futures['tt'].result()
            logger.debug(f"TT calculated successfully: {tt}")
        
            pt: PT_DTO = futures['pt'].result()
            logger.debug(f"PT calculated successfully: {pt}")

        tfst_calc: TFSTCalculationDTO = self.tfst_calculator.calculate(alpha=alpha, pt=pt, tt=tt)
        tfst: TFST_DTO = TFST_DTO(
            lower=tfst_calc.lower,
            upper=tfst_calc.upper,
            alpha=tfst_calc.alpha,
            tolerance=self.tolerance,
            computed=to_compute
        )
        logger.debug(f"TFST calculated successfully: {tfst}")

        return TFSTExecutorResult(alpha=alpha, pt=pt, tt=tt, tfst=tfst)

    def _execute_sequential(
        self,
        time_sequence: TimeSequenceDTO,
        alpha: AlphaDTO,
        pt_input: PTInputDTO,
        tt_input: TTInputDTO
    ) -> TFSTExecutorResult:
        
        to_compute: TFSTCompute = self._optimize_by_alpha(alpha)
        
        if to_compute == TFSTCompute.PT or to_compute == TFSTCompute.ALL:
            pt: PT_DTO = self.pt_calculator.calculate(pt_input, time_sequence)
            logger.debug(f"PT calculated successfully: {pt}")
        else:
            pt: PT_DTO = self.pt_calculator.empty_path_dto()
            logger.debug("PT calculation skipped due to negligible weight")

        if to_compute == TFSTCompute.TT or to_compute == TFSTCompute.ALL:
            tt: TT_DTO = self.tt_calculator.calculate(tt_input, time_sequence)
            logger.debug(f"TT calculated successfully: {tt}")
        else:
            tt: TT_DTO = self.tt_calculator.empty()
            logger.debug("TT calculation skipped due to negligible weight")

        tfst_calculation: TFSTCalculationDTO = self.tfst_calculator.calculate(pt=pt, tt=tt, alpha=alpha)
        tfst: TFST_DTO = TFST_DTO(
            lower=tfst_calculation.lower,
            upper=tfst_calculation.upper,
            alpha=tfst_calculation.alpha,
            tolerance=self.tolerance,
            computed=to_compute
        )
        logger.debug(f"TFST calculated successfully: {tfst}")

        return TFSTExecutorResult(alpha=alpha, pt=pt, tt=tt, tfst=tfst)