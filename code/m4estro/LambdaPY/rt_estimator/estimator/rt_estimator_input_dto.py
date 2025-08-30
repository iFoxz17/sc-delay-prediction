from typing import List
from pydantic import BaseModel, Field

class RTEstimatorInputDTO(BaseModel):
    latitude_source: float = Field(..., description="Latitude of the source location", ge=-90.0, le=90.0)
    longitude_source: float = Field(..., description="Longitude of the source location", ge=-180.0, le=180.0)

    latitude_destination: float = Field(..., description="Latitude of the destination location", ge=-90.0, le=90.0)
    longitude_destination: float = Field(..., description="Longitude of the destination location", ge=-180.0, le=180.0)

    distance: float = Field(..., description="Distance between source and destination in meters", ge=0.0)

    tmi: float = Field(..., description="Traffic Meta Index value", ge=0.0, le=1.0)
    avg_tmi: float = Field(..., description="Average Traffic Meta Index value", ge=0.0, le=1.0)

    wmi: float = Field(..., description="Weather Meta Index value", ge=0.0, le=1.0)
    avg_wmi: float = Field(..., description="Average Weather Meta Index value", ge=0.0, le=1.0)

    avg_oti: float = Field(..., description="Average Overall Transit Index value", ge=0.0)

class RTEstimatorBatchInputDTO(BaseModel):
    batch: List[RTEstimatorInputDTO] = Field(
        ...,
        description="List of route time estimator input DTOs"
    )