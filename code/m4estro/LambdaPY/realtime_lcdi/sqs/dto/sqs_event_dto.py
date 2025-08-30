from typing import Union

from sqs.dto.order_event_dto import OrderEventDataDTO
from sqs.dto.disruption_event_dto import DisruptionEventDataDTO

from enum import Enum
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class EventType(Enum):
    DISRUPTION_ALERT = "DISRUPTION_EVENT"
    TRACKING_EVENT = "TRACKING_UPDATE"

SqsEventDataDTO = Union[DisruptionEventDataDTO, OrderEventDataDTO]

class SqsEvent(BaseModel):
    event_type: EventType = Field(
        ..., 
        alias="eventType",
        description="Type of the event, e.g., DISRUPTION_EVENT or ORDER_EVENT"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: SqsEventDataDTO = Field(..., description="Data specific to the event type")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


