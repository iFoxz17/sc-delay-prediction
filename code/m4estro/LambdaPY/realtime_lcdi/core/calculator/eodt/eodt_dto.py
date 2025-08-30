from dataclasses import dataclass, field

@dataclass(frozen=True)
class EODT_DTO:
   value: float = field(metadata={"description": "The value of the EODT (Estimated Order Delivery Time) in hours."})