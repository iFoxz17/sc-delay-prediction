from typing import Tuple
from dataclasses import dataclass
from datetime import datetime

from stats_utils import compute_gamma_ci, compute_sample_ci

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.tfst.tfst_dto import TFSTCalculationDTO

from core.calculator.dt.dt_input_dto import DTDistributionDTO, DTGammaDTO, DTSampleDTO
from core.calculator.dt.dt_dto import DT_DTO

from core.calculator.time_deviation.time_deviation_input_dto import TimeDeviationInputDTO, STDistributionDTO, STGammaDTO, STSampleDTO
from core.calculator.time_deviation.time_deviation_dto import TimeDeviationDTO

from logger import get_logger
logger = get_logger(__name__)

@dataclass(frozen=True)
class TimeDeviationResult:
    lower: float
    upper: float

class TimeDeviationCalculator:
    def __init__(self, dispatch_confidence: float, shipment_confidence: float) -> None:
        self.dispatch_confidence: float = dispatch_confidence
        self.shipment_confidence: float = shipment_confidence

    def _calculate_dt_time_deviation(self, dt_distribution: DTDistributionDTO, dt: DT_DTO) -> TimeDeviationResult:
        dt_ci: Tuple[float, float] = (0.0, 0.0)
        
        if isinstance(dt_distribution, DTGammaDTO):
            dt_gamma: DTGammaDTO = dt_distribution
            dt_ci: Tuple[float, float] = compute_gamma_ci(
                shape=dt_gamma.shape, 
                scale=dt_gamma.scale,
                loc=dt_gamma.loc,
                confidence_level=self.dispatch_confidence
            )
            logger.debug(f"Computed DT confidence interval from gamma distribution for time deviation calculation: {dt_ci}")
        elif isinstance(dt_distribution, DTSampleDTO):
            dt_sample: DTSampleDTO = dt_distribution
            dt_ci: Tuple[float, float] = compute_sample_ci(
                x=dt_sample.x,
                confidence_level=self.dispatch_confidence
            )
            logger.debug(f"Computed DT confidence interval from sample distribution for time deviation calculation: {dt_ci}")
        else:
            logger.error(f"Unsupported DT distribution type: {type(dt_distribution)}. This should never happen.")
            raise ValueError(
                f"Unsupported DT distribution type: {type(dt_distribution)}. This should never happen."
            )
        
        dt_threshold: float = dt_ci[1]
        return TimeDeviationResult(lower = dt.total_time_lower - dt_threshold, upper = dt.total_time_upper - dt_threshold)

    def _calculate_st_time_deviation(self, st_distribution: STDistributionDTO, shipment_time: datetime, estimation_time: datetime, tfst: TFSTCalculationDTO) -> TimeDeviationResult:
        st_ci: Tuple[float, float] = (0.0, 0.0)
        
        if isinstance(st_distribution, STGammaDTO):
            st_gamma: STGammaDTO = st_distribution
            st_ci: Tuple[float, float] = compute_gamma_ci(
                shape=st_gamma.shape, 
                scale=st_gamma.scale,
                loc=st_gamma.loc,
                confidence_level=self.shipment_confidence
            )
            logger.debug(f"Computed ST confidence interval from gamma distribution for time deviation calculation: {st_ci}")
        elif isinstance(st_distribution, STSampleDTO):
            st_sample: STSampleDTO = st_distribution
            st_ci: Tuple[float, float] = compute_sample_ci(
                x=st_sample.x,
                confidence_level=self.shipment_confidence
            )
            logger.debug(f"Computed ST confidence interval from sample distribution for time deviation calculation: {st_ci}")
        else:
            logger.error(f"Unsupported ST distribution type: {type(st_distribution)}. This should never happen.")
            raise ValueError(
                f"Unsupported ST distribution type: {type(st_distribution)}. This should never happen."
            )
        
        st_threshold: float = st_ci[1]
        logger.debug(f"ST threshold for time deviation calculation: {st_threshold}")

        elapsed_time: float = (estimation_time - shipment_time).total_seconds() / 3600.0
        logger.debug(f"Elapsed time: {elapsed_time} hours")

        expected_time_upper: float = tfst.upper + elapsed_time
        expected_time_lower: float = tfst.lower + elapsed_time
        logger.debug(f"Expected total time upper: {expected_time_upper}, Expected total time lower: {expected_time_lower}")

        return TimeDeviationResult(lower = expected_time_lower - st_threshold, upper = expected_time_upper - st_threshold)

    def calculate(self, td_input: TimeDeviationInputDTO, time_sequence: TimeSequenceDTO) -> TimeDeviationDTO:
        shipment_time: datetime = time_sequence.shipment_time

        dt_time_deviation: TimeDeviationResult = self._calculate_dt_time_deviation(
            dt_distribution=td_input.td_partial_input.dt_distribution,
            dt=td_input.dt
        )
        st_time_deviation: TimeDeviationResult = self._calculate_st_time_deviation(
            st_distribution=td_input.td_partial_input.st_distribution,
            shipment_time=shipment_time,
            estimation_time=time_sequence.shipment_estimation_time,
            tfst=td_input.tfst,
        )

        return TimeDeviationDTO(
            dt_td_lower=dt_time_deviation.lower,
            dt_td_upper=dt_time_deviation.upper,
            st_td_lower=st_time_deviation.lower,
            st_td_upper=st_time_deviation.upper,
            dt_confidence=self.dispatch_confidence,
            st_confidence=self.shipment_confidence
        )