from typing import List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class OrderEventType(str, Enum):
    ORDER_CREATION = "ORDER_CREATION"
    CARRIER_CREATION = "CARRIER_CREATION"
    CARRIER_UPDATE = "CARRIER_UPDATE"
    CARRIER_DELIVERY = "CARRIER_DELIVERY"
    
class OrderEventDataDTO(BaseModel):
    type_: OrderEventType = Field(..., alias="type")
    order_id: int = Field(..., alias="orderId")
    tracking_number: str = Field(..., alias="trackingNumber")
    event_timestamps: List[str] = Field(..., alias="eventTimestamps")
    order_new_steps_ids: List[int] = Field(..., alias="orderNewStepsIds")
    order_new_locations: List[str] = Field(..., alias="orderNewLocations")

    model_config = ConfigDict(extra="ignore", populate_by_name=True)