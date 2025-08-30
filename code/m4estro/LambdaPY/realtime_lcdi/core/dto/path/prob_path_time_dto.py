from typing import Annotated, override
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, model_validator

from core.dto.path.prob_path_dto import ProbPathIdDTO, ProbPathNameDTO

class ProbPathTimeBaseDTO(ABC, BaseModel):
    lower_time: Annotated[float, Field(..., ge=0.0, description="Lower time for the path in hours.")]
    upper_time: Annotated[float, Field(..., ge=0.0, description="Upper time for the path in hours.")]

    avg_tmi: Annotated[float, Field(..., ge=0.0, le=1.0, description="Weighted average of the TMI for the routes of the first vertex.")]
    avg_wmi: Annotated[float, Field(..., ge=0.0, le=1.0, description="Weighted average of the WMI for the routes of the first vertex.")]

    @abstractmethod
    def _is_abstract(self) -> bool:
        pass

class ProbPathIdTimeDTO(ProbPathTimeBaseDTO, ProbPathIdDTO):
    @override
    def _is_abstract(self) -> bool:
        return False
    
    @model_validator(mode="after")
    def validate_model(self) -> 'ProbPathIdTimeDTO':
        if self.lower_time > self.upper_time:
            raise ValueError("Lower time cannot be greater than upper time.")
        return self
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "path": [1, 2, 4],
                "prob": 0.55,
                "carrier": "dhl",
                "lower_time": 10.0,
                "upper_time": 12.0,
                "avg_tmi": 0.2,
                "avg_wmi": 0.3
            }
        }
    }

class ProbPathNameTimeDTO(ProbPathTimeBaseDTO, ProbPathNameDTO):
    @override
    def _is_abstract(self) -> bool:
        return False

    @model_validator(mode="after")
    def validate_model(self) -> 'ProbPathNameTimeDTO':
        if self.lower_time > self.upper_time:
            raise ValueError("Lower time cannot be greater than upper time.")
        return self
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "path": ["vertex1", "vertex2", "vertex4"],
                "prob": 0.55,
                "carrier": "dhl",
                "lower_time": 10.0,
                "upper_time": 12.0,
                "avg_tmi": 0.2,
                "avg_wmi": 0.3
            }
        }
    }
    