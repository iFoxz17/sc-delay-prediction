from typing import List, Union, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, model_validator, RootModel
from pydantic.config import ConfigDict

from resolver.vertex_dto import VertexDTO

class OrderEstimationRequestDTO(BaseModel):
    order_id: int = Field(
        ..., 
        alias="orderId",
        description="Unique identifier for the order."
    )
    event_time: datetime = Field(
        ..., 
        alias="eventTime",
        description="Timestamp of the carrier event related to the order."
    )
    estimation_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="estimationTime",
        description="Timestamp for the estimation process. Defaults to the current time in UTC."
    )
    vertex: Optional[VertexDTO] = Field(
        default=None,
        description="Vertex object descriptor"
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

class OrderEstimationRequestListDTO(RootModel[List[OrderEstimationRequestDTO]]):

    @model_validator(mode="after")
    def check_not_empty(self):
        if not self.root:
            raise ValueError("Request list must not be empty.")
        return self

# Union alias for input handling
OrderEstimationRequest = Union[OrderEstimationRequestDTO, OrderEstimationRequestListDTO]
