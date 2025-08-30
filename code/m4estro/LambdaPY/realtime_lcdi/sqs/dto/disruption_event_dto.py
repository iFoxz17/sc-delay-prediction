from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict


class AffectedOrderSummaryDTO(BaseModel):
    order_ids: List[int] = Field(..., alias="orderIds")
    statuses: List[str]
    locations: List[str]

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class AffectedOrdersDTO(BaseModel):
    total: int
    summary: AffectedOrderSummaryDTO

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class DisruptionLocationDTO(BaseModel):
    name: str
    coordinates: List[float]
    radius_km: float = Field(..., alias="radiusKm")

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class DisruptionDTO(BaseModel):
    disruption_type: str = Field(..., alias="disruptionType")
    disruption_location: DisruptionLocationDTO = Field(..., alias="disruptionLocation")
    measurements: Dict[str, float]

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class DisruptionEventDataDTO(BaseModel):
    event_timestamp: str = Field(..., alias="eventTimestamp")
    disruption: DisruptionDTO
    affected_orders: AffectedOrdersDTO = Field(..., alias="affectedOrders")

    model_config = ConfigDict(extra="ignore", populate_by_name=True)