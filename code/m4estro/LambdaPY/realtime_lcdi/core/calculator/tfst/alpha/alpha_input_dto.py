from typing import Union, Optional
from dataclasses import dataclass, field

import igraph as ig

@dataclass(frozen=True)
class AlphaGammaDTO:
    shape: float
    scale: float
    loc: float

@dataclass(frozen=True)
class AlphaSampleDTO:
    mean: float

AlphaDistributionDTO = Union[AlphaGammaDTO, AlphaSampleDTO]

@dataclass(frozen=True)
class AlphaBaseInputDTO:
    st_distribution: AlphaDistributionDTO = field(
        metadata={"description": "Shipment time distribution parameters for the Alpha calculation, either gamma or sample distribution"},
    )

    vertex_id: Optional[int] = field(
        default=None,
        metadata={"description": "Id of the actual vertex for the Markov alpha calculation, if applicable"},
    )

@dataclass(frozen=True)
class AlphaInputDTO(AlphaBaseInputDTO):
    pass