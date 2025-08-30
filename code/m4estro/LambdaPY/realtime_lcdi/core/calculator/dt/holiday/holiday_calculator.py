from typing import Optional, List, Dict, TYPE_CHECKING
import math
from datetime import timedelta, date

from utils.config import WEEK_DAY_MAP, get_week_day
from service.db_utils import get_read_only_db_connector
from service.read_only_db_connector import ReadOnlyDBConnector

from model.holiday import Holiday, HolidayCategory
from model.site import Site

from core.calculator.dt.holiday.holiday_input_dto import HolidayInputDTO, HolidayPeriodInputDTO, HolidayADTInputDTO
from core.calculator.dt.holiday.holiday_dto import HolidayDTO, HolidayResultDTO

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from model.country import Country

from logger import get_logger
logger = get_logger(__name__)

DAYS_WINDOW: int = 30

class HolidayCalculator:

    def __init__(self, 
                 consider_closure_holidays: bool,
                 consider_working_holidays: bool,
                 consider_weekends_holidays: bool,
                 maybe_days_window: Optional[int] = None,
                 maybe_ro_db_connector: Optional[ReadOnlyDBConnector] = None
                 ) -> None:
        
        self.consider_closure_holidays: bool = consider_closure_holidays
        self.consider_weekends_holidays: bool = consider_weekends_holidays
        self.consider_working_holidays: bool = consider_working_holidays

        self.days_window: int = maybe_days_window or DAYS_WINDOW
        self.ro_db_connector: ReadOnlyDBConnector = maybe_ro_db_connector or get_read_only_db_connector()

    def _load_holidays(self, country: 'Country', from_: date, to: date, session: 'Session') -> List[Holiday]:
        holidays = session.query(Holiday).filter(
            Holiday.country == country,
            Holiday.date >= from_,
            Holiday.date <= to
        ).all()

        logger.debug(f"Loaded {len(holidays)} holidays for country {country.code} from {from_} to {to}.")

        return holidays
    
    def _is_weekend(self, holiday_by_year_day: Dict[int, Holiday], country: 'Country', date_: date) -> Optional[HolidayDTO]:            
        weekend_start: int = country.weekend_start
        weekend_end: int = country.weekend_end
        week_day: int = get_week_day(date_)
        
        if not weekend_start <= week_day <= weekend_end:
            return None 

        week_day_name: str = WEEK_DAY_MAP[week_day]
        return HolidayDTO(
            id=0,
            name=f"Weekend - {week_day_name}",
            country=country.code,
            date=date_,
            category=HolidayCategory.CLOSURE.value,
            type='Public',
            description=f"Weekend closure on {week_day_name}"
        )
    
    def _is_holiday(self, holiday_by_year_day: Dict[int, Holiday], date_: date, holiday_category: HolidayCategory) -> Optional[HolidayDTO]:
        year_day: int = date_.timetuple().tm_yday

        if year_day in holiday_by_year_day:
            holiday: Holiday = holiday_by_year_day[year_day] 
            if holiday.category == holiday_category:
                return HolidayDTO(
                    id=holiday.id,
                    name=holiday.name,
                    country=holiday.country_code,
                    date=date_,
                    category=holiday.category.value,
                    type=holiday.type or 'Unknown',
                    description=holiday.description or 'No description available'
                )
        
        return None
    
    def _is_working_holiday(self, holiday_by_year_day: Dict[int, Holiday], date_: date) -> Optional[HolidayDTO]:
        return self._is_holiday(holiday_by_year_day, date_, HolidayCategory.WORKING)
    
    def _is_closure_holiday(self, holiday_by_year_day: Dict[int, Holiday], date_: date) -> Optional[HolidayDTO]:
        return self._is_holiday(holiday_by_year_day, date_, HolidayCategory.CLOSURE)

    def _index_holidays(self, holidays: List[Holiday]) -> Dict[int, Holiday]:
        holidays_by_year_day: Dict[int, Holiday] = {}
        for holiday in holidays:
            year_day: int = holiday.date.timetuple().tm_yday
            holidays_by_year_day[year_day] = holiday

        logger.debug(f"Indexed {len(holidays_by_year_day)} holidays by year day.")
        
        return holidays_by_year_day
    
    def _retrieve_holidays_from_period(self, start_date: date, end_date: date, site_id: int) -> HolidayResultDTO:
        with self.ro_db_connector.session_scope() as session:
            site: Site = session.query(Site).filter(Site.id == site_id).one()
            country: 'Country' = site.location.country
            logger.debug(f"Data for site {site_id} with country {country.code} loaded successfully.")

            possible_holidays: List[Holiday] = self._load_holidays(country, start_date, end_date + timedelta(days=self.days_window), session)

        consider_closure_holidays: bool = site.consider_closure_holidays and self.consider_closure_holidays
        consider_working_holidays: bool = site.consider_working_holidays and self.consider_working_holidays
        consider_weekends_holidays: bool = site.consider_weekends_holidays and self.consider_weekends_holidays
        
        if not consider_closure_holidays and not consider_working_holidays and not consider_weekends_holidays:
            logger.debug("No holidays considered after applying site configuration, skipping holiday retrieval.")
            return HolidayResultDTO(
                consider_closure_holidays=False,
                consider_working_holidays=False,
                consider_weekends_holidays=False,
                closure_holidays=[],
                working_holidays=[],
                weekend_holidays=[]
            )

        holiday_index: Dict[int, Holiday] = self._index_holidays(possible_holidays)

        actual_date: date = start_date

        closure_holidays: List[HolidayDTO] = []
        working_holidays: List[HolidayDTO] = []
        weekend_holidays: List[HolidayDTO] = []

        logger.debug(
            f"Starting holiday retrieval from {start_date} to {end_date} for site {site_id} ({site.location_name}) with: "
            f"consider_closure_holidays={consider_closure_holidays}, "
            f"consider_weekends_holidays={consider_weekends_holidays}, "
            f"consider_working_holidays={consider_working_holidays})"
        )

        for _ in range((end_date - start_date).days + 1):
            found_holiday: bool = False

            if consider_closure_holidays:
                maybe_closure_holiday: Optional[HolidayDTO] = self._is_closure_holiday(holiday_index, actual_date)
                if maybe_closure_holiday is not None:
                    found_holiday = True
                    closure_holidays.append(maybe_closure_holiday)
                    logger.debug(f"Found closure holiday on {actual_date}: {maybe_closure_holiday.name}.")
            if consider_working_holidays and not found_holiday:
                maybe_working_holiday: Optional[HolidayDTO] = self._is_working_holiday(holiday_index, actual_date)
                if maybe_working_holiday is not None:
                    found_holiday = True
                    working_holidays.append(maybe_working_holiday)
                    logger.debug(f"Found working holiday on {actual_date}: {maybe_working_holiday.name}.")
            if consider_weekends_holidays and not found_holiday:
                maybe_weekend: Optional[HolidayDTO] = self._is_weekend(holiday_index, country, actual_date)
                if maybe_weekend is not None:
                    found_holiday = True
                    weekend_holidays.append(maybe_weekend)
                    logger.debug(f"Found weekend day on {actual_date}: {maybe_weekend.name}.")
                                    
            if not found_holiday:
                logger.debug(f"No holiday found on {actual_date}.")

            actual_date += timedelta(days=1)
    
        return HolidayResultDTO(
            consider_closure_holidays=consider_closure_holidays,
            consider_working_holidays=consider_working_holidays,
            consider_weekends_holidays=consider_weekends_holidays,
            closure_holidays=closure_holidays,
            working_holidays=working_holidays,
            weekend_holidays=weekend_holidays
        )


    def _calculate_holidays_from_adt(self, start_date: date, adt: float, site_id: int) -> HolidayResultDTO:
        dispatch_days: int = math.ceil(adt / 24.0)
        end_date: date = start_date + timedelta(days=dispatch_days)

        with self.ro_db_connector.session_scope() as session:
            site: Site = session.query(Site).filter(Site.id == site_id).one()
            country: 'Country' = site.location.country
            logger.debug(f"Data for site {site_id} with country {country.code} loaded successfully.")

            possible_holidays: List[Holiday] = self._load_holidays(country, start_date, end_date + timedelta(days=self.days_window), session)

        consider_closure_holidays: bool = site.consider_closure_holidays and self.consider_closure_holidays
        consider_working_holidays: bool = site.consider_working_holidays and self.consider_working_holidays
        consider_weekends_holidays: bool = site.consider_weekends_holidays and self.consider_weekends_holidays
        
        if not consider_closure_holidays and not consider_working_holidays and not consider_weekends_holidays:
            logger.debug("No holidays considered after applying site configuration, skipping holiday calculation.")
            return HolidayResultDTO(
                consider_closure_holidays=False,
                consider_working_holidays=False,
                consider_weekends_holidays=False,
                closure_holidays=[],
                working_holidays=[],
                weekend_holidays=[]
            )

        holiday_index: Dict[int, Holiday] = self._index_holidays(possible_holidays)

        actual_date: date = start_date

        closure_holidays: List[HolidayDTO] = []
        working_holidays: List[HolidayDTO] = []
        weekend_holidays: List[HolidayDTO] = []

        logger.debug(
            f"Starting holiday calculation from {start_date} to {end_date} ({dispatch_days} dispatch days) for site {site_id} ({site.location_name}) with: "
            f"consider_closure_holidays={consider_closure_holidays}, "
            f"consider_weekends_holidays={consider_weekends_holidays}, "
            f"consider_working_holidays={consider_working_holidays})"
        )

        while dispatch_days > 0:
            found_holiday: bool = False

            if consider_closure_holidays:
                maybe_closure_holiday: Optional[HolidayDTO] = self._is_closure_holiday(holiday_index, actual_date)
                if maybe_closure_holiday is not None:
                    found_holiday = True
                    closure_holidays.append(maybe_closure_holiday)
                    logger.debug(f"Found closure holiday on {actual_date}: {maybe_closure_holiday.name}. Remaining dispatch days: {dispatch_days}")
            if consider_working_holidays and not found_holiday:
                maybe_working_holiday: Optional[HolidayDTO] = self._is_working_holiday(holiday_index, actual_date)
                if maybe_working_holiday is not None:
                    found_holiday = True
                    working_holidays.append(maybe_working_holiday)
                    dispatch_days -= 1
                    logger.debug(f"Found working holiday on {actual_date}: {maybe_working_holiday.name}. Remaining dispatch days: {dispatch_days}")
            if consider_weekends_holidays and not found_holiday:
                maybe_weekend: Optional[HolidayDTO] = self._is_weekend(holiday_index, country, actual_date)
                if maybe_weekend is not None:
                    found_holiday = True
                    weekend_holidays.append(maybe_weekend)
                    logger.debug(f"Found weekend day on {actual_date}: {maybe_weekend.name}. Remaining dispatch days: {dispatch_days}")
                                    
            if not found_holiday:
                dispatch_days -= 1
                logger.debug(f"No holiday found on {actual_date}. Remaining dispatch days: {dispatch_days}")

            actual_date += timedelta(days=1)

        return HolidayResultDTO(
            consider_closure_holidays=consider_closure_holidays,
            consider_working_holidays=consider_working_holidays,
            consider_weekends_holidays=consider_weekends_holidays,
            closure_holidays=closure_holidays,
            working_holidays=working_holidays,
            weekend_holidays=weekend_holidays
        )
    
    def retrieve_holidays(self, holiday_input: HolidayPeriodInputDTO) -> HolidayResultDTO:
        return self._retrieve_holidays_from_period(
            start_date=holiday_input.start_time.date(),
            end_date=holiday_input.end_time.date(),
            site_id=holiday_input.site_id,
        )

    def calculate_holidays(self, holiday_input: HolidayADTInputDTO) -> HolidayResultDTO:
        return self._calculate_holidays_from_adt(
            start_date=holiday_input.start_time.date(),
            adt=holiday_input.adt,
            site_id=holiday_input.site_id,
        )

    
    def calculate(self, holiday_input: HolidayInputDTO) -> HolidayResultDTO:
        if not self.consider_closure_holidays and not self.consider_working_holidays and not self.consider_weekends_holidays:
            logger.debug("No holidays considered from holiday calculator configuration, skipping calculation.")
            return HolidayResultDTO(
                consider_closure_holidays=False,
                consider_working_holidays=False,
                consider_weekends_holidays=False,
                closure_holidays=[],
                working_holidays=[],
                weekend_holidays=[]
            )
        
        if isinstance(holiday_input, HolidayPeriodInputDTO):
           return self.retrieve_holidays(holiday_input)
    
        if isinstance(holiday_input, HolidayADTInputDTO):
           return self.calculate_holidays(holiday_input)
        
        logger.error(f"Unsupported HolidayInputDTO type: {type(holiday_input)}. This should never happen.")
        raise ValueError(f"Unsupported HolidayInputDTO type: {type(holiday_input)}. This should never happen.")