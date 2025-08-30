from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, ConfigDict, model_serializer

class ExternalDisruptionDTO(BaseModel):
    disruption_type: str = Field(..., alias="disruptionType")
    severity: float

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

class DelayDTO(BaseModel):
    dispatch_lower: float
    dispatch_upper: float
    shipment_lower: float
    shipment_upper: float
    expected_order_delivery_time: datetime
    estimated_order_delivery_time: datetime

    @property
    def total_lower(self) -> float:
        return self.dispatch_lower + self.shipment_lower
    
    @property
    def total_upper(self) -> float:
        return self.dispatch_upper + self.shipment_upper

    @classmethod
    def from_dict(cls, delay: Dict[str, Dict[str, float]], expected_dt: datetime, estimated_dt: datetime) -> "DelayDTO":
        return cls(
            dispatch_lower=delay["dispatch"]["lower"],
            dispatch_upper=delay["dispatch"]["upper"],
            shipment_lower=delay["shipment"]["lower"],
            shipment_upper=delay["shipment"]["upper"],
            expected_order_delivery_time=expected_dt,
            estimated_order_delivery_time=estimated_dt
        )

    @model_serializer(mode="wrap")
    def to_dict(self, handler):
        return {
            "dispatch": {"lower": self.dispatch_lower, "upper": self.dispatch_upper},
            "shipment": {"lower": self.shipment_lower, "upper": self.shipment_upper},
            "total": {"lower": self.total_lower, "upper": self.total_upper}
        }

class ReconfigurationEvent(BaseModel):
    order_id: int = Field(..., alias="orderId")
    sls: bool = Field(..., alias="SLS")
    external: Optional[ExternalDisruptionDTO] = None
    delay: Optional[DelayDTO] = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    @classmethod
    def from_et(cls, et_data: Dict[str, Any], external: Optional[ExternalDisruptionDTO] = None, maybe_sls: Optional[bool] = None) -> "ReconfigurationEvent":
        order_id: int = et_data['order']['id']
        sls: bool = maybe_sls or et_data['order']['SLS']
        
        delay_dict: Dict[str, Dict[str, float]] = et_data['indicators']['delay']
        edd: datetime = datetime.fromisoformat(et_data['indicators']['EDD'])
        expected_ddt: datetime = edd - timedelta(hours=(delay_dict['total']['lower'] + delay_dict['total']['upper']) / 2)

        delay: DelayDTO = DelayDTO.from_dict(
            delay=delay_dict, 
            estimated_dt=edd, 
            expected_dt=expected_ddt
            )

        return cls(
            orderId=order_id,
            SLS=sls,
            external=external,
            delay=delay
        )
