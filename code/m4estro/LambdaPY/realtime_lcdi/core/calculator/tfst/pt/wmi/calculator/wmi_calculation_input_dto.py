from typing import List
from dataclasses import dataclass

@dataclass(frozen=True)
class WMICalculationInputDTO:
    weather_codes: List[str]
    temperature_celsius: List[float]