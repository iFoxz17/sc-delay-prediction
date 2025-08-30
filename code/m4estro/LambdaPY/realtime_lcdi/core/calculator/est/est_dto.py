from dataclasses import dataclass, field

@dataclass(frozen=True)
class EST_DTO:
   value: float = field(metadata={"description": "The value of the EST (Estimated Shipment Time) in hours."})