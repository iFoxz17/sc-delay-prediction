from dataclasses import dataclass
from datetime import datetime, timedelta

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO, TimeSequenceInputDTO, EstimationStage
from core.dto.dto_factory import DTOFactory

from core.calculator.dt.dt_calculator import DTCalculator
from core.calculator.dt.dt_input_dto import DTInputDTO
from core.calculator.dt.dt_dto import DT_DTO

from core.calculator.tfst.alpha.alpha_input_dto import AlphaBaseInputDTO, AlphaInputDTO

from core.calculator.tfst.pt.pt_input_dto import PTInputDTO, PTBaseInputDTO

from core.calculator.tfst.tt.tt_input_dto import TTInputDTO, TTBaseInputDTO

from core.calculator.tfst.tfst_dto import TFST_DTO
from core.executor.tfst_executor import TFSTExecutorResult, TFSTExecutor

from core.calculator.est.est_calculator import ESTCalculator
from core.calculator.est.est_dto import EST_DTO

from core.calculator.cfdi.cfdi_calculator import CFDICalculator
from core.calculator.cfdi.cfdi_dto import CFDI_DTO

from core.calculator.eodt.eodt_calculator import EODTCalculator
from core.calculator.eodt.eodt_dto import EODT_DTO

from core.calculator.edd.edd_calculator import EDDCalculator
from core.calculator.edd.edd_dto import EDD_DTO

from core.calculator.time_deviation.time_deviation_calculator import TimeDeviationCalculator
from core.calculator.time_deviation.time_deviation_input_dto import TimeDeviationBaseInputDTO, TimeDeviationInputDTO
from core.calculator.time_deviation.time_deviation_dto import TimeDeviationDTO

from logger import get_logger
logger = get_logger(__name__)

@dataclass
class ExecutorResult:
    time_sequence: TimeSequenceDTO
    dt: DT_DTO
    tfst_executor_result: TFSTExecutorResult
    est: EST_DTO
    cfdi: CFDI_DTO
    eodt: EODT_DTO
    edd: EDD_DTO
    time_deviation: TimeDeviationDTO

class Executor:
    def __init__(self, 
                 dto_factory: DTOFactory,
                 dt_calculator: DTCalculator,
                 tfst_calculator_executor: TFSTExecutor,
                 est_calculator: ESTCalculator,
                 cfdi_calculator: CFDICalculator,
                 eodt_calculator: EODTCalculator,
                 edd_calculator: EDDCalculator,
                 td_calculator: TimeDeviationCalculator
                 ) -> None:
        
        self.dto_factory: DTOFactory = dto_factory

        self.dt_calculator: DTCalculator = dt_calculator
        self.tfst_calculator_executor: TFSTExecutor = tfst_calculator_executor
        self.est_calculator: ESTCalculator = est_calculator
        self.cfdi_calculator: CFDICalculator = cfdi_calculator
        self.eodt_calculator: EODTCalculator = eodt_calculator
        self.edd_calculator: EDDCalculator = edd_calculator
        self.td_calculator: TimeDeviationCalculator = td_calculator

    def execute(
            self,
            time_sequence_input: TimeSequenceInputDTO,
            dt_input: DTInputDTO,
            alpha_base_input: AlphaBaseInputDTO,
            pt_base_input: PTBaseInputDTO,
            tt_base_input: TTBaseInputDTO,
            td_partial_input: TimeDeviationBaseInputDTO
    ) -> ExecutorResult:
        
        dt: DT_DTO = self.dt_calculator.calculate(dt_input=dt_input, time_sequence_input=time_sequence_input)
        logger.debug(f"DT calculated successfully: {dt}")

        order_time: datetime = time_sequence_input.order_time
        shipment_time: datetime = order_time + timedelta(hours=dt.total_time)

        time_sequence: TimeSequenceDTO = TimeSequenceDTO(
            order_time=order_time,
            shipment_time=shipment_time,
            event_time=time_sequence_input.event_time,
            estimation_time=time_sequence_input.estimation_time
        )
        logger.debug(f"Built valid time sequence for stage {time_sequence.get_estimation_stage().value}: {time_sequence}")

        alpha_input: AlphaInputDTO = self.dto_factory.create_alpha_input_dto(alpha_base_input=alpha_base_input)
        pt_input: PTInputDTO = self.dto_factory.create_pt_input_dto(pt_base_input=pt_base_input)
        tt_input: TTInputDTO = self.dto_factory.create_tt_input_dto(tt_partial_input=tt_base_input)

        tfst_executor_result: TFSTExecutorResult = self.tfst_calculator_executor.execute(
            time_sequence=time_sequence,
            alpha_input=alpha_input,
            pt_input=pt_input,
            tt_input=tt_input
        )
        tfst: TFST_DTO = tfst_executor_result.tfst

        est: EST_DTO = self.est_calculator.calculate(tfst)
        logger.debug(f"EST calculated successfully: {est}")

        cfdi: CFDI_DTO = self.cfdi_calculator.calculate(tfst=tfst, est=est)
        logger.debug(f"CFDI calculated successfully: {cfdi}")
        
        eodt: EODT_DTO = self.eodt_calculator.calculate(time_sequence=time_sequence, est=est)
        logger.debug(f"EODT calculated successfully: {eodt}")
        
        edd: EDD_DTO = self.edd_calculator.calculate(time_sequence=time_sequence, eodt=eodt)
        logger.debug(f"EDD calculated successfully: {edd}")

        td_input: TimeDeviationInputDTO = self.dto_factory.create_time_deviation_input_dto(
            td_partial_input=td_partial_input,
            dt=dt,
            tfst=tfst
        )
        time_deviation: TimeDeviationDTO = self.td_calculator.calculate(td_input=td_input, time_sequence=time_sequence)
        logger.debug(f"Time deviation calculated successfully: {time_deviation}")
        
        return ExecutorResult(
            tfst_executor_result=tfst_executor_result,
            dt=dt,
            est=est,
            cfdi=cfdi,
            eodt=eodt,
            edd=edd,
            time_deviation=time_deviation,
            time_sequence=time_sequence
        )