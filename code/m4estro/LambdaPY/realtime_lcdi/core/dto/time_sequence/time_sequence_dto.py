from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, model_validator

from core.exception.invalid_time_sequence_exception import InvalidTimeSequenceException

class EstimationStage(Enum):
    DISPATCH = "dispatch"
    SHIPMENT = "shipment"
    DELIVERY = "delivery"

class TimeSequenceInputDTO(BaseModel):
    order_time: datetime = Field(
        ...,
        description="Starting time of the order (timestamp of the manufacturer order creation, e.g. t0)"
    )
    event_time: datetime = Field(
        ...,
        description="Time of the last recorded event"
    )
    estimation_time: datetime = Field(
        ...,
        description="Time when the estimation is made (e.g. t)"
    )

    @model_validator(mode="after")
    def validate_input_time_sequence(self):
        if self.estimation_time < self.event_time:
            raise InvalidTimeSequenceException(f"Estimation time cannot be earlier than event time.",
                                               order_time=self.order_time,
                                               event_time=self.event_time,
                                               estimation_time=self.estimation_time)
        if self.event_time < self.order_time:
            raise InvalidTimeSequenceException(f"Event time cannot be earlier than order time.",
                                               order_time=self.order_time,
                                               event_time=self.event_time,
                                               estimation_time=self.estimation_time)
        return self

    model_config = ConfigDict(frozen=True, extra="forbid")

class TimeSequenceDTO(TimeSequenceInputDTO):
    shipment_time: datetime = Field(
        ...,
        description="Starting time of the shipment (timestamp of the first carrier event, e.g. t1)"
    )

    @property
    def shipment_event_time(self) -> datetime:
        return max(self.event_time, self.shipment_time)
    
    @property
    def shipment_estimation_time(self) -> datetime:
        return max(self.estimation_time, self.shipment_time)

    @model_validator(mode="after")
    def validate_time_sequence(self):
        if self.shipment_time < self.order_time:
            raise InvalidTimeSequenceException("Shipment time cannot be earlier than order time.",
                             order_time=self.order_time,
                             maybe_shipment_time=self.shipment_time,
                             event_time=self.event_time,
                             estimation_time=self.estimation_time)
        
        if self.event_time < self.shipment_time < self.estimation_time:
            raise InvalidTimeSequenceException("Shipment time cannot be earlier than event time and later than estimation time.",
                             order_time=self.order_time,
                             maybe_shipment_time=self.shipment_time,
                             event_time=self.event_time,
                             estimation_time=self.estimation_time)
        return self

    model_config = ConfigDict(frozen=True, extra="forbid")

    def get_estimation_stage(self) -> EstimationStage:
        if self.estimation_time < self.shipment_time:
            return EstimationStage.DISPATCH
        
        return EstimationStage.SHIPMENT