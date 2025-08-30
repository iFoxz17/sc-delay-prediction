from typing import List
from pydantic import BaseModel, Field

class RTEstimatorOutputDTO(BaseModel):
    time: float = Field(
        ...,
        description="Estimated time to travel from source to destination in hours",
        ge=0.0
    )

class RTEstimatorBatchOutputDTO(BaseModel):
    batch: List[RTEstimatorOutputDTO] = Field(
        ...,
        description="List of estimated times for each route in hours"
    )