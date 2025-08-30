from abc import ABC
from dataclasses import dataclass
from datetime import datetime

@dataclass
class HolidayInputDTO(ABC):
    start_time: datetime
    site_id: int

@dataclass
class HolidayPeriodInputDTO(HolidayInputDTO):
    end_time: datetime

@dataclass
class HolidayADTInputDTO(HolidayInputDTO):
    adt: float