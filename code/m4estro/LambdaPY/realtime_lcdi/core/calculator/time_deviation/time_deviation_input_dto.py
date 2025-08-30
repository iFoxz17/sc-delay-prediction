from typing import Union, List
from dataclasses import dataclass

from core.calculator.dt.dt_input_dto import DTDistributionDTO
from core.calculator.dt.dt_dto import DT_DTO

from core.calculator.tfst.tfst_dto import TFSTCalculationDTO

@dataclass(frozen=True)
class STGammaDTO:
    shape: float
    scale: float
    loc: float

@dataclass(frozen=True)
class STSampleDTO:
    x: List[float]
    mean: float

STDistributionDTO = Union[STGammaDTO, STSampleDTO]

@dataclass(frozen=True)
class TimeDeviationBaseInputDTO:
    dt_distribution: DTDistributionDTO
    st_distribution: STDistributionDTO

@dataclass(frozen=True)
class TimeDeviationInputDTO:
    td_partial_input: TimeDeviationBaseInputDTO
    dt: DT_DTO
    tfst: TFSTCalculationDTO
