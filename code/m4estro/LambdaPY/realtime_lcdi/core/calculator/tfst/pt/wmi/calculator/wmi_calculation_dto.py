from enum import Enum

from dataclasses import dataclass

class By(Enum):
    WEATHER_CONDITION = "weather_condition"
    TEMPERATURE = "temperature"
    NONE = "none"

@dataclass(frozen=True)
class WMICalculationDTO:
    value: float
    weather_code: str
    weather_description: str
    temperature_celsius: float
    by: By

    