from typing import Union, List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class OrderEstimationStatus(str, Enum):
    CREATED = "CREATED"
    FAILED = "FAILED"
    ERROR = "ERROR"

class OrderEstimationCreatedDTO(BaseModel):
    status: OrderEstimationStatus = OrderEstimationStatus.CREATED
    id: int = Field(..., description="Unique identifier for the created estimation resource.",)
    location: str = Field(..., description="URL of the created estimation resource.",) 
    data: Optional[Dict[str, Any]] = Field(default=None, description="Estimation data")

class OrderEstimationFailedDTO(BaseModel):
    status: OrderEstimationStatus = OrderEstimationStatus.FAILED
    message: str = Field(..., description="Message indicating the reason for the failure.",)

class OrderEstimationErrorDTO(BaseModel):
    status: OrderEstimationStatus = OrderEstimationStatus.ERROR
    message: str = Field(..., description="Message indicating the reason for the error.",)


OrderEstimationResponseDTO = Union[OrderEstimationCreatedDTO, OrderEstimationFailedDTO, OrderEstimationErrorDTO]
OrderEstimationResponse = Union[OrderEstimationResponseDTO, List[OrderEstimationResponseDTO]]
