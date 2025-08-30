from typing import Union
from pydantic import BaseModel, Field, ConfigDict

class CarrierIdDTO(BaseModel):
    carrier_id: int = Field(
        ..., 
        alias="carrierId",
        description="Unique identifier for the carrier."
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

class CarrierNameDTO(BaseModel):
    carrier_name: str = Field(
        ..., 
        alias="carrierName",
        description="Unique name for the carrier"
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

CarrierDTO = Union[CarrierIdDTO, CarrierNameDTO]
