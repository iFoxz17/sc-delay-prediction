from typing import TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
   from core.executor.tfst_executor import TFSTCompute

@dataclass(frozen=True)
class TFSTCalculationDTO:
   lower: float = field(metadata={"description": "The lower bound of the TFST (Transit Forecastasted Shipment Time) in hours."})
   upper: float = field(metadata={"description": "The upper bound of the TFST (Transit Forecastasted Shipment Time) in hours."})
   alpha: float = field(metadata={"description": "The alpha value for the TFST (Transit Forecastasted Shipment Time) calculation."})


@dataclass(frozen=True)
class TFST_DTO(TFSTCalculationDTO):

   tolerance: float = field(metadata={"description": "The tolerance level for the TFST calculation."})
   computed: 'TFSTCompute' = field(metadata={"description": "Indicates which components were computed in the TFST calculation."})