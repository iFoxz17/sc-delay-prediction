from typing import List, Union

from dataclasses import dataclass

from model.shipment_time_gamma import ShipmentTimeGamma
from model.shipment_time_sample import ShipmentTimeSample
from model.dispatch_time_gamma import DispatchTimeGamma
from model.dispatch_time_sample import DispatchTimeSample

@dataclass(frozen=True)
class ShipmentTimeGammaResult:
    dt_gamma: ShipmentTimeGamma

@dataclass(frozen=True)
class ShipmentTimeSampleResult:
    dt_sample: ShipmentTimeSample
    dt_x: List[float]

ShipmentTimeResult = Union[ShipmentTimeGammaResult, ShipmentTimeSampleResult]

@dataclass(frozen=True)
class DispatchTimeGammaResult:
    dt_gamma: DispatchTimeGamma

@dataclass(frozen=True)
class DispatchTimeSampleResult:
    dt_x: List[float]
    dt_sample: DispatchTimeSample

DispatchTimeResult = Union[DispatchTimeGammaResult, DispatchTimeSampleResult]
    