from typing import Optional
from datetime import datetime

class InvalidTimeSequenceException(Exception):    
    def __init__(self, 
                 message: str, 
                 order_time: datetime, 
                 event_time: datetime, 
                 estimation_time: datetime,
                 maybe_shipment_time: Optional[datetime] = None, 
                 ) -> None:
        super().__init__(message)

        self.message: str = message
        self.order_time: datetime = order_time
        self.event_time: datetime = event_time
        self.estimation_time: datetime = estimation_time
        self.maybe_shipment_time: Optional[datetime] = maybe_shipment_time

    def __str__(self) -> str:
        if self.maybe_shipment_time is None:
            return (f"{self.message}: "
                    f"Order time: {self.order_time}, "
                    f"Event time: {self.event_time}, "
                    f"Estimation time: {self.estimation_time}"
                    f"Shipment time not provided.")
        
        return (f"{self.message}: "
                f"Order time: {self.order_time}, "
                f"Shipment time: {self.maybe_shipment_time}, "
                f"Event time: {self.event_time}, "
                f"Estimation time: {self.estimation_time}")