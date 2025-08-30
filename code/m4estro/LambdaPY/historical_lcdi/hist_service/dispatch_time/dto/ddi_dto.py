from dataclasses import dataclass

@dataclass(frozen=True)
class DDI_DTO:
    lower: float
    upper: float