from dataclasses import dataclass

@dataclass(frozen=True)
class CTDI_DTO:
    lower: float
    upper: float