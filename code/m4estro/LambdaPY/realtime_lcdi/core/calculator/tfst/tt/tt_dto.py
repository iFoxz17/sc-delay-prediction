from dataclasses import dataclass, field

@dataclass(frozen=True)
class TT_DTO:
    lower: float = field(metadata={"description": "Lower bound of the TT (Transit Time) in hours"})
    upper: float = field(metadata={"description": "Upper bound of the TT (Transit Time) in hours"})
    confidence: float = field(metadata={"description": "Confidence level of the TT (Transit Time)"})