from typing import Tuple
from datetime import datetime

from stats_utils import compute_gamma_mean, compute_gamma_ci, compute_sample_ci

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO, TimeSequenceInputDTO

from core.calculator.dt.holiday.holiday_calculator import HolidayCalculator
from core.calculator.dt.holiday.holiday_input_dto import HolidayADTInputDTO, HolidayInputDTO, HolidayPeriodInputDTO
from core.calculator.dt.holiday.holiday_dto import HolidayResultDTO

from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.dt.dt_input_dto import (
    DTInputDTO, 
    DTShipmentTimeInputDTO,
    DTDistributionInputDTO,
    DTDistributionDTO, 
    DTGammaDTO,
    DTSampleDTO
)

from logger import get_logger
logger = get_logger(__name__)

class DTCalculator:
    def __init__(self, holiday_calculator: HolidayCalculator, confidence: float) -> None:
        self._holiday_calculator: HolidayCalculator = holiday_calculator
        self.confidence: float = confidence

    def _calculate_distribution_dt(self, dt_input: DTDistributionInputDTO, time_sequence_input: TimeSequenceInputDTO) -> DT_DTO:
        logger.debug(f"Calculating DT for site {dt_input.site_id} from distribution input: {dt_input.distribution}")

        adt: float
        dispatch_ci: Tuple[float, float]

        dt_distribution: DTDistributionDTO = dt_input.distribution 

        order_time: datetime = time_sequence_input.order_time
        estimation_time: datetime = time_sequence_input.estimation_time
        
        if isinstance(dt_distribution, DTGammaDTO):
            dt_gamma: DTGammaDTO = dt_distribution
            adt: float = compute_gamma_mean(
                shape=dt_gamma.shape, 
                scale=dt_gamma.scale,
                loc=dt_gamma.loc
            )
            logger.debug(f"Computed ADT from gamma distribution: {adt}")
            dispatch_ci: Tuple[float, float] = compute_gamma_ci(
                shape=dt_gamma.shape, 
                scale=dt_gamma.scale,
                loc=dt_gamma.loc,
                confidence_level=self.confidence
            )
            logger.debug(f"Computed dispatch confidence interval from gamma distribution: {dispatch_ci}")
        elif isinstance(dt_distribution, DTSampleDTO):
            dt_sample: DTSampleDTO = dt_distribution
            adt: float = dt_sample.mean
            logger.debug(f"Computed ADT from sample distribution: {adt}")
            dispatch_ci: Tuple[float, float] = compute_sample_ci(
                x=dt_sample.x,
                confidence_level=self.confidence
            )
            logger.debug(f"Computed dispatch confidence interval from sample distribution: {dispatch_ci}")
        else:
            logger.error(f"Unsupported DT distribution type: {type(dt_distribution)}. This should never happen.")
            raise ValueError(
                f"Unsupported DT distribution type: {type(dt_distribution)}. This should never happen."
            )
        
        dispatch_time_lower: float = dispatch_ci[0]
        dispatch_time_upper: float = dispatch_ci[1]
                           
        elapsed_time: float = (estimation_time - order_time).total_seconds() / 3600.0
        logger.debug(f"Elapsed time from order time to estimation time: {elapsed_time} hours")

        logger.debug(f"Calculating elapsed holidays from {order_time} to {estimation_time} for site {dt_input.site_id}")
        elapsed_holiday_input: HolidayInputDTO = HolidayPeriodInputDTO(
            start_time=time_sequence_input.order_time,
            end_time=time_sequence_input.estimation_time,
            site_id=dt_input.site_id,
        )
        elapsed_holiday_result: HolidayResultDTO = self._holiday_calculator.calculate(holiday_input=elapsed_holiday_input)
        logger.debug(f"Elapsed holidays: {elapsed_holiday_result}")

        elapsed_working_time: float = max(elapsed_time - elapsed_holiday_result.n_closure_days * 24.0, 0.0)
        logger.debug(f"Elapsed working time: {elapsed_working_time} hours")
    
        remaining_working_time_lower: float = dispatch_time_lower - elapsed_working_time
        if remaining_working_time_lower < 0:
            logger.warning(f"Found negative remaining working time: {remaining_working_time_lower} hours. Setting to 0.")
            remaining_working_time_lower = 0.0
        logger.debug(f"Remaining working time: {remaining_working_time_lower} hours")

        remaining_working_time: float = adt - elapsed_working_time
        if remaining_working_time < 0:
            logger.warning(f"Found negative remaining working time: {remaining_working_time} hours. Setting to 0.")
            remaining_working_time = 0.0

        remaining_working_time_upper: float = dispatch_time_upper - elapsed_working_time
        if remaining_working_time_upper < 0:
            logger.warning(f"Found negative remaining working time: {remaining_working_time_upper} hours. Setting to 0.")
            remaining_working_time_upper = 0.0
        logger.debug(f"Remaining working time upper bound: {remaining_working_time_upper} hours")

        if not remaining_working_time_lower <= remaining_working_time <= remaining_working_time_upper:
            logger.error(f"Remaining working time {remaining_working_time} is not within bounds: [{remaining_working_time_lower}, {remaining_working_time_upper}]. This should never happen.")

        remaining_holiday_input: HolidayInputDTO = HolidayADTInputDTO(
            start_time=estimation_time,
            adt=remaining_working_time,
            site_id=dt_input.site_id,
        )
        remaining_holiday_result: HolidayResultDTO = self._holiday_calculator.calculate(holiday_input=remaining_holiday_input)
        logger.debug(f"Remaining holidays: {remaining_holiday_result}")
        holidays_closure_hours: float = remaining_holiday_result.n_closure_days * 24.0

        remaining_time_lower: float = remaining_working_time_lower + holidays_closure_hours
        logger.debug(f"Remaining time from estimation time to shipment time: {remaining_time_lower} hours")

        remaining_time: float = remaining_working_time + holidays_closure_hours
        logger.debug(f"Remaining lower time from estimation time to shipment time: {remaining_time} hours")

        remaining_time_upper: float = remaining_working_time_upper + holidays_closure_hours
        logger.debug(f"Remaining upper time from estimation time to shipment time: {remaining_time_upper} hours")

        return DT_DTO(
            confidence=self.confidence,
            elapsed_time=elapsed_time,
            elapsed_working_time=elapsed_working_time,
            elapsed_holidays=elapsed_holiday_result,
            remaining_time_lower=remaining_time_lower,
            remaining_time=remaining_time,
            remaining_time_upper=remaining_time_upper,
            remaining_working_time_lower=remaining_working_time_lower,
            remaining_working_time=remaining_working_time,
            remaining_working_time_upper=remaining_working_time_upper,
            remaining_holidays=remaining_holiday_result,
        )
        
    def _calculate_shipment_dt(self, dt_input: DTShipmentTimeInputDTO, time_sequence_input: TimeSequenceInputDTO) -> DT_DTO:
        logger.debug(f"Calculating DT for site {dt_input.site_id} from shipment time input: {dt_input.shipment_time}")
        
        t0: datetime = time_sequence_input.order_time
        t1: datetime = dt_input.shipment_time

        holiday_input: HolidayInputDTO = HolidayPeriodInputDTO(
            start_time=t0,
            end_time=t1,
            site_id=dt_input.site_id,
        )
        holiday_result: HolidayResultDTO = self._holiday_calculator.calculate(holiday_input=holiday_input)
        logger.debug(f"Holidays from order time to shipment time: {holiday_result}")

        elapsed_time: float = (t1 - t0).total_seconds() / 3600.0
        logger.debug(f"Elapsed time from order time to shipment time: {elapsed_time} hours")
        
        elapsed_working_time: float = elapsed_time - holiday_result.n_closure_days * 24.0
        if elapsed_working_time < 0:
            logger.warning(f"Found negative elapsed working time: {elapsed_working_time} hours. Setting to 0.")
            elapsed_working_time = 0.0
        logger.debug(f"Elapsed working time from order time to shipment time: {elapsed_working_time} hours")

        return DT_DTO(
            confidence=self.confidence,
            elapsed_time=elapsed_time,
            elapsed_working_time=elapsed_working_time,
            elapsed_holidays=holiday_result,
            remaining_time_lower=0.0,
            remaining_time=0.0,
            remaining_time_upper=0.0,
            remaining_working_time_lower=0.0,
            remaining_working_time=0.0,
            remaining_working_time_upper=0.0,
            remaining_holidays=HolidayResultDTO(
                consider_closure_holidays=self._holiday_calculator.consider_closure_holidays,
                consider_working_holidays=self._holiday_calculator.consider_working_holidays,
                consider_weekends_holidays=self._holiday_calculator.consider_weekends_holidays,
                closure_holidays=[],
                working_holidays=[],
                weekend_holidays=[]
            ),
        )

    def calculate(self, dt_input: DTInputDTO, time_sequence_input: TimeSequenceInputDTO) -> DT_DTO:
        if isinstance(dt_input, DTDistributionInputDTO):
            dt: DT_DTO = self._calculate_distribution_dt(dt_input, time_sequence_input)

        elif isinstance(dt_input, DTShipmentTimeInputDTO):
            dt: DT_DTO = self._calculate_shipment_dt(dt_input, time_sequence_input)

        else:
            logger.error(f"Unsupported DT input type: {type(dt_input)}. This should never happen.")
            raise ValueError(
                f"Unsupported DT input type: {type(dt_input)}. This should never happen."
            )
        
        return dt