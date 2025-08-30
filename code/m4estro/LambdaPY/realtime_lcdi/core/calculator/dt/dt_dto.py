from dataclasses import dataclass, field

from core.calculator.dt.holiday.holiday_dto import HolidayResultDTO

@dataclass(frozen=True)
class DT_DTO:
   
   confidence: float = field(metadata={"description": "Confidence level for the DT calculation."})

   elapsed_time: float = field(metadata={"description": "Elapsed time in hours from order time to estimation time."})
   elapsed_working_time: float = field(metadata={"description": "Elapsed working time in hours from order time to estimation time."})
   elapsed_holidays: HolidayResultDTO = field(metadata={"description": "Elapsed holidays from order time to estimation time, if holidays are considered."})

   remaining_time_lower: float = field(metadata={"description": "Lower bound of remaining time in hours from estimation time to shipment time."})
   remaining_time: float = field(metadata={"description": "Estimated remaining time in hours from estimation time to shipment time."})
   remaining_time_upper: float = field(metadata={"description": "Upper bound of remaining time in hours from estimation time to shipment time."})

   remaining_working_time_lower: float = field(metadata={"description": "Lower bound of remaining working time in hours from estimation time to shipment time."})
   remaining_working_time: float = field(metadata={"description": "Estimated remaining working time in hours from estimation time to shipment time."})
   remaining_working_time_upper: float = field(metadata={"description": "Upper bound of remaining working time in hours from estimation time to shipment time."})

   remaining_holidays: HolidayResultDTO = field(metadata={"description": "Remaining holidays for the estimated time to shipment time, if holidays are considered."})
   
   @property
   def total_time_lower(self) -> float:
      return self.elapsed_time + self.remaining_time_lower
   
   @property
   def total_time_upper(self) -> float:
      return self.elapsed_time + self.remaining_time_upper
   
   @property
   def total_time(self) -> float:
      return self.elapsed_time + self.remaining_time

   @property
   def total_working_time_lower(self) -> float:
      return self.elapsed_working_time + self.remaining_working_time_lower

   @property
   def total_working_time_upper(self) -> float:
      return self.elapsed_working_time + self.remaining_working_time_upper

   @property
   def total_working_time(self) -> float:
      return self.elapsed_working_time + self.remaining_working_time

   
   @property
   def total_holidays(self) -> HolidayResultDTO:
      return HolidayResultDTO(
         consider_closure_holidays=self.elapsed_holidays.consider_closure_holidays or self.remaining_holidays.consider_closure_holidays,
         consider_working_holidays=self.elapsed_holidays.consider_working_holidays or self.remaining_holidays.consider_working_holidays,
         consider_weekends_holidays=self.elapsed_holidays.consider_weekends_holidays or self.remaining_holidays.consider_weekends_holidays,
         closure_holidays=self.elapsed_holidays.closure_holidays + self.remaining_holidays.closure_holidays,
         working_holidays=self.elapsed_holidays.working_holidays + self.remaining_holidays.working_holidays,
         weekend_holidays=self.elapsed_holidays.weekend_holidays + self.remaining_holidays.weekend_holidays
      )