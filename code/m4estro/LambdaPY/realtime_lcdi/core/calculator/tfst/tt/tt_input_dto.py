from typing import Union, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

@dataclass(frozen=True)
class TTGammaDTO:
    shape: float
    scale: float
    loc: float

@dataclass(frozen=True)
class TTSampleDTO:
    x: List[float]
    mean: float

TTDistributionDTO = Union[TTGammaDTO, TTSampleDTO]

@dataclass(frozen=True)
class TTBaseInputDTO:
    distribution: TTDistributionDTO = field(
        metadata={"description": "Distribution parameters for the TT calculation, either gamma or sample distribution"},
    )

@dataclass(frozen=True)
class TTInputDTO(TTBaseInputDTO):
    pass