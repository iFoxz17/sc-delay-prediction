from typing import List, Annotated, override
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

Probability = Annotated[float, Field(..., ge=0.0, le=1.0, description="Probability of the path, must be between 0 and 1.")]

PathId = Annotated[List[int], Field(..., min_length=0, description="A path represented as a list of vertex ids.")]
PathName = Annotated[List[str], Field(..., min_length=0, description="A path represented as a list of vertex names.")]

class ProbPathBaseDTO(ABC, BaseModel):
    prob: Probability
    carrier: str = Field(..., description="Name of the carrier associated with this path.")

    @abstractmethod
    def _is_abstract(self) -> bool:
        pass

class ProbPathIdDTO(ProbPathBaseDTO):
    path: PathId

    @override
    def _is_abstract(self) -> bool:
        return False

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "path": [1, 2, 4],
                "prob": 0.55,
                "carrier": "dhl"
            }
        }
    }

class ProbPathNameDTO(ProbPathBaseDTO):
    path: PathName

    @override
    def _is_abstract(self) -> bool:
        return False

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "path": ["vertex1", "vertex2", "vertex4"],
                "prob": 0.55,
                "carrier": "dhl"
            }
        }
    }