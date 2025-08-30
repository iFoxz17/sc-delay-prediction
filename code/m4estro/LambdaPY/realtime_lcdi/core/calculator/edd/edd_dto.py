from datetime import datetime
from dataclasses import dataclass, field

@dataclass(frozen=True)
class EDD_DTO:
   value: datetime = field(metadata={"description": "The value of the EDD (Estimated Delivery Date) as a datetime object."})