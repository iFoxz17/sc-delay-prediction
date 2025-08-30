from typing import Optional
from dataclasses import dataclass

from service.read_only_db_connector import ReadOnlyDBConnector

from core.query_handler.params.params_result import (
    DTParams,
    TFSTParams,
    TimeDeviationParams,
    ParamsResult
)

from core.calculator.dt.dt_calculator import DTCalculator
from core.calculator.dt.holiday.holiday_calculator import HolidayCalculator
from core.initializer.tfst_initializer import TFSTInitializer, TFSTInitializerResult
from core.calculator.est.est_calculator import ESTCalculator
from core.calculator.cfdi.cfdi_calculator import CFDICalculator
from core.calculator.eodt.eodt_calculator import EODTCalculator
from core.calculator.edd.edd_calculator import EDDCalculator
from core.calculator.time_deviation.time_deviation_calculator import TimeDeviationCalculator

from logger import get_logger
logger = get_logger(__name__)

@dataclass
class InitializerResult:
    dt_calculator: DTCalculator
    tfst_initializer_result: TFSTInitializerResult
    est_calculator: ESTCalculator
    cfdi_calculator: CFDICalculator
    eodt_calculator: EODTCalculator
    edd_calculator: EDDCalculator
    time_deviation_calculator: TimeDeviationCalculator

class Initializer:
    def __init__(self, tfst_initializer: TFSTInitializer) -> None:
        self.tfst_initializer: TFSTInitializer = tfst_initializer

    def initialize(self, 
                   params: ParamsResult,
                   maybe_ro_db_connector: Optional[ReadOnlyDBConnector] = None
    ) -> InitializerResult:
        
        dt_params: DTParams = params.dt_params
        tfst_params: TFSTParams = params.tfst_params
        time_deviation_params: TimeDeviationParams = params.time_deviation_params
        
        holiday_calculator: HolidayCalculator = HolidayCalculator(
            consider_closure_holidays=dt_params.holidays_params.consider_closure_holidays,
            consider_working_holidays=dt_params.holidays_params.consider_working_holidays,
            consider_weekends_holidays=dt_params.holidays_params.consider_weekends_holidays,
            maybe_ro_db_connector=maybe_ro_db_connector
        )
        logger.debug("Holiday calculator initialized successfully")

        dt_calculator = DTCalculator(holiday_calculator=holiday_calculator, confidence=dt_params.confidence)
        logger.debug("DT calculator initialized successfully")

        tfst_initializer_result: TFSTInitializerResult = self.tfst_initializer.initialize(tfst_params)

        est_calculator: ESTCalculator = ESTCalculator()
        logger.debug("EST calculator initialized successfully")

        cfdi_calculator: CFDICalculator = CFDICalculator()
        logger.debug("CFDI calculator initialized successfully")

        eodt_calculator: EODTCalculator = EODTCalculator()
        logger.debug("EODT calculator initialized successfully")

        edd_calculator: EDDCalculator = EDDCalculator()
        logger.debug("EDD calculator initialized successfully")

        time_deviation_calculator: TimeDeviationCalculator = TimeDeviationCalculator(
            dispatch_confidence=time_deviation_params.dt_time_deviation_confidence,
            shipment_confidence=time_deviation_params.st_time_deviation_confidence,
        )
        logger.debug("Time Deviation calculator initialized successfully")

        return InitializerResult(
            dt_calculator=dt_calculator,
            tfst_initializer_result=tfst_initializer_result,
            est_calculator=est_calculator,
            cfdi_calculator=cfdi_calculator,
            eodt_calculator=eodt_calculator,
            edd_calculator=edd_calculator,
            time_deviation_calculator=time_deviation_calculator
        )