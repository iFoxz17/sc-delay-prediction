from typing import Union, List
from datetime import datetime
from dataclasses import dataclass, field

@dataclass(frozen=True)
class DTBaseInputDTO:
    site_id: int = field(metadata={"description": "ID of the site for which the DT is calculated."})

@dataclass(frozen=True)
class DTGammaDTO:
    shape: float
    scale: float
    loc: float

@dataclass(frozen=True)
class DTSampleDTO:
    x: List[float]
    mean: float

DTDistributionDTO = Union[DTGammaDTO, DTSampleDTO]

@dataclass(frozen=True)
class DTDistributionInputDTO(DTBaseInputDTO):
    distribution: DTDistributionDTO = field(
        metadata={"description": "Distribution parameters for the DT calculation, either gamma or sample distribution"},
    )

@dataclass(frozen=True)
class DTShipmentTimeInputDTO(DTBaseInputDTO):
    shipment_time: datetime = field(
        metadata={"description": "Starting time of the shipment (timestamp of the first carrier event, e.g. t1)"},
    )

DTInputDTO = Union[DTDistributionInputDTO, DTShipmentTimeInputDTO]