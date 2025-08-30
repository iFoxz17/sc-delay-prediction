from typing import List, Dict, Any
from datetime import date 
from dataclasses import dataclass

@dataclass
class HolidayDTO:
    id: int
    name: str
    country: str
    date: date
    category: str
    type: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "date": self.date.isoformat(),
            "category": self.category,
            "type": self.type,
            "description": self.description
        }
    
@dataclass
class HolidayResultDTO:
    consider_closure_holidays: bool
    consider_working_holidays: bool
    consider_weekends_holidays: bool
    
    closure_holidays: List[HolidayDTO]
    working_holidays: List[HolidayDTO]
    weekend_holidays: List[HolidayDTO]
    
    @property
    def n_closure_days(self) -> int:
        return len(self.closure_holidays) + len(self.weekend_holidays)
    
    @property
    def closure_days(self) -> List[HolidayDTO]:
        return self.closure_holidays + self.weekend_holidays