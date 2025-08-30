from dataclasses import dataclass, field

@dataclass(frozen=True)
class CFDI_DTO:
   lower: float = field(metadata={"description": "The lower bound of the CFDI (Carrier Delay Forecast Index) in hours."})
   upper: float = field(metadata={"description": "The upper bound of the CFDI (Carrier Delay Forecast Index) in hours."})