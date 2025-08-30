from typing import List
from datetime import datetime
from dataclasses import dataclass, field

@dataclass(frozen=True)
class PTBaseInputDTO:
    vertex_id: int = field(
        metadata={"description": "ID of the vertex for which the path time estimate is calculated."}
    )

    carrier_names: List[str] = field(
        metadata={"description": "List of carrier names to be considered for the path time estimate."},
    )

@dataclass(frozen=True)
class PTInputDTO(PTBaseInputDTO):
    pass