from typing import List, Annotated, override
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, model_validator, ConfigDict

from core.dto.path.prob_path_dto import ProbPathIdDTO, ProbPathNameDTO

EPSILON = 1e-3

Carriers = Annotated[List[str], Field(description="List of all the carrier names associated with at least one path.")]

class PathsBaseDTO(BaseModel, ABC):
    requested_carriers: Carriers = Field(..., alias="requestedCarriers",)
    valid_carriers: Carriers = Field(..., alias="validCarriers")

    @abstractmethod
    def _is_abstract(self) -> bool:
        pass

    model_config = ConfigDict(populate_by_name=True)

class PathsIdDTO(PathsBaseDTO):
    source: Annotated[int, Field(..., ge=0, description="Id of the source vertex (non-negative).")]
    destination: Annotated[int, Field(..., ge=0, description="id of the destination vertex (non-negative).")]

    paths: List[ProbPathIdDTO] = Field(
        ...,
        description="List of all possible paths from source to destination with their associated probabilities and carrier."
    )

    @override
    def _is_abstract(self) -> bool:
        return False

    @property
    def total_probability(self) -> float:
        return sum(p.prob for p in self.paths)

    @property
    def n_paths(self) -> int:
        return len(self.paths)
    
    @model_validator(mode="after")
    def validate_model(self) -> 'PathsIdDTO':
        if not (abs(self.total_probability - 1.0) < EPSILON or abs(self.total_probability) < EPSILON):
            raise ValueError("Sum of 'probs' must be equal to 1.0 or to 0.0.")
        return self
    
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class PathsNameDTO(PathsBaseDTO):
    source: Annotated[str, Field(..., description="Name of the source vertex (non-empty string).")]
    destination: Annotated[str, Field(..., description="Name of the destination vertex (non-empty string).")]

    paths: List[ProbPathNameDTO] = Field(
        ...,
        description="List of all possible paths from source to destination with their associated probabilities and carrier."
    )

    @override
    def _is_abstract(self) -> bool:
        return False

    @property
    def total_probability(self) -> float:
        return sum(p.prob for p in self.paths)

    @property
    def n_paths(self) -> int:
        return len(self.paths)
    
    @model_validator(mode="after")
    def validate_model(self) -> 'PathsNameDTO':
        if not (abs(self.total_probability - 1.0) < EPSILON or abs(self.total_probability) < EPSILON):
            raise ValueError("Sum of 'probs' must be equal to 1.0 or to 0.0.")
        return self
    
    model_config = ConfigDict(extra="forbid", validate_assignment=True)