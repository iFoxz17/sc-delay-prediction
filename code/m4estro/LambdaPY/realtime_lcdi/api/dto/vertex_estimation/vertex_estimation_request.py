from typing import List, Union, Optional
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, RootModel
from pydantic.config import ConfigDict

from resolver.vertex_dto import VertexDTO
from api.dto.carrier_dto import CarrierDTO
from api.dto.site_dto import SiteDTO

class VertexEstimationRequestDTO(BaseModel):
    vertex: VertexDTO = Field(..., description="Vertex object descriptor")
    carrier: CarrierDTO = Field(..., description="Carrier object descriptor")
    site: SiteDTO = Field(..., description="Site object descriptor")
    
    order_time: datetime = Field(
        ...,
        alias="orderTime",
        description="Timestamp of the order event (e.g. of the time the order was confirmed)."
    )
    event_time: datetime = Field(
        ...,
        alias="eventTime",
        description="Timestamp of the last event (both dispatch or shipment event)."
    )
    estimation_time: datetime = Field(
        ...,
        alias="estimationTime",
        description="Timestamp to start the estimation process with."
    )
    maybe_shipment_time: Optional[datetime] = Field(
        default=None,
        alias="shipmentTime",
        description="Timestamp of the first carrier event (e.g. of the time the shipment started) or None."
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class VertexEstimationRequestListDTO(RootModel[List[VertexEstimationRequestDTO]]):

    @model_validator(mode="after")
    def check_not_empty(self):
        if not self.root:
            raise ValueError("Request list must not be empty.")
        return self

# Union alias for input handling
VertexEstimationRequest = Union[VertexEstimationRequestDTO, VertexEstimationRequestListDTO]