from typing import Dict, Any, List, TYPE_CHECKING, Optional
import pydantic
from datetime import datetime
from pydantic import BaseModel, Field

class OrderPatchDTO(BaseModel):
    manufacturer_estimated_delivery: Optional[datetime] = Field(
        default=None,
        description="The estimated delivery date from the manufacturer"
    )

    manufacturer_confirmed_delivery: Optional[datetime] = Field(
        default=None,
        description="The confirmed delivery date from the manufacturer"
    )

    srs: Optional[bool] = Field(
        default=None,
        description="Shipment Reordering System (SRS), indicating the presence of quality issues"
    )
