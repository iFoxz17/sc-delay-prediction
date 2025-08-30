import pytest
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model.country import Country
from model.location import Location
from model.site import Site
from model.supplier import Supplier
from model.holiday import Holiday, HolidayCategory, Base

from core.calculator.dt.holiday.holiday_input_dto import HolidayInputDTO, HolidayPeriodInputDTO, HolidayADTInputDTO
from core.calculator.dt.holiday.holiday_calculator import HolidayCalculator
from service.read_only_db_connector import ReadOnlyDBConnector


@pytest.fixture
def in_memory_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def populated_session(in_memory_session):
    country = Country(
        code="XX",
        name="Testland",
        total_holidays=10,
        weekend_start=6,
        weekend_end=7
    )
    location = Location(name="Testville", country=country, city="Test City", state="Test State", latitude=12.34, longitude=56.78)
    supplier = Supplier(name="Test Supplier", manufacturer_supplier_id="TS123")
    site = Site(
        id=1,
        supplier=supplier,
        location=location,
        consider_closure_holidays=True,
        consider_weekends_holidays=True,
        consider_working_holidays=True
    )

    christmas = Holiday(
        name="Christmas",
        date=date(2024, 12, 25),
        country=country,
        country_code="XX",
        category=HolidayCategory.CLOSURE,
        type="NATIONAL",
        description="Christmas Day",
        week_day=3,
        month=12,
        year_day=360,
        url=None
    )
    working_holiday = Holiday(
        name="Working Sunday",
        date=date(2024, 12, 22),
        country=country,
        country_code="XX",
        category=HolidayCategory.WORKING,
        type="EXCEPTION",
        description="Open on Sunday",
        week_day=1,
        month=12,
        year_day=358,
        url=None
    )

    in_memory_session.add_all([site, christmas, working_holiday])
    in_memory_session.commit()
    return in_memory_session


class FakeReadOnlyDBConnector(ReadOnlyDBConnector):
    def __init__(self, session):
        self._session = session

    def session_scope(self):  # type: ignore
        class DummyContext:
            def __enter__(inner_self):  # type: ignore
                return self._session

            def __exit__(inner_self, exc_type, exc_val, exc_tb):  # type: ignore
                pass

        return DummyContext()


def test_holiday_retrieval_closure_only(populated_session):
    fake_connector = FakeReadOnlyDBConnector(populated_session)
    calculator = HolidayCalculator(
        consider_closure_holidays=True,
        consider_weekends_holidays=False,
        consider_working_holidays=False,
        maybe_ro_db_connector=fake_connector,
        maybe_days_window=10
    )

    holiday_input = HolidayPeriodInputDTO(
        start_time=datetime(2024, 12, 21),
        end_time=datetime(2024, 12, 25),
        site_id=1
    )

    result = calculator.calculate(holiday_input)

    assert result.n_closure_days == 1
    assert len(result.closure_holidays) == 1
    assert result.closure_holidays[0].name == "Christmas"
    assert result.closure_holidays[0].date == date(2024, 12, 25)
    assert result.weekend_holidays == []
    assert result.working_holidays == []

def test_holiday_calculation_closure_only(populated_session):
    fake_connector = FakeReadOnlyDBConnector(populated_session)
    calculator = HolidayCalculator(
        consider_closure_holidays=True,
        consider_weekends_holidays=False,
        consider_working_holidays=False,
        maybe_ro_db_connector=fake_connector,
        maybe_days_window=10
    )

    holiday_input = HolidayADTInputDTO(
        start_time=datetime(2024, 12, 21),
        adt=24.0 * 5,
        site_id=1
    )

    result = calculator.calculate(holiday_input)

    assert result.n_closure_days == 1
    assert len(result.closure_holidays) == 1
    assert result.closure_holidays[0].name == "Christmas"
    assert result.closure_holidays[0].date == date(2024, 12, 25)
    assert result.weekend_holidays == []
    assert result.working_holidays == []


def test_holiday_retrieval_no_working_holidays(populated_session):
    fake_connector = FakeReadOnlyDBConnector(populated_session)
    calculator = HolidayCalculator(
        consider_closure_holidays=True,
        consider_working_holidays=False,
        consider_weekends_holidays=True,
        maybe_ro_db_connector=fake_connector,
        maybe_days_window=10
    )

    holiday_input = HolidayPeriodInputDTO(
        start_time=datetime(2024, 12, 21, 23, 0, 0),
        end_time=datetime(2024, 12, 24, 1, 0, 0),
        site_id=1,
    )

    result = calculator.calculate(holiday_input)

    closure_dates = {h.date for h in result.closure_holidays}
    weekend_dates = {h.date for h in result.weekend_holidays}
    working_holiday_dates = {h.date for h in result.working_holidays}

    assert closure_dates == set()
    assert date(2024, 12, 21) in weekend_dates           # Saturday
    assert date(2024, 12, 22) in weekend_dates           # Sunday
    assert working_holiday_dates == set()                # No working holidays
    assert result.n_closure_days == 2

def test_holiday_calculation_no_working_holidays(populated_session):
    fake_connector = FakeReadOnlyDBConnector(populated_session)
    calculator = HolidayCalculator(
        consider_closure_holidays=True,
        consider_working_holidays=False,
        consider_weekends_holidays=True,
        maybe_ro_db_connector=fake_connector,
        maybe_days_window=10
    )

    holiday_input = HolidayADTInputDTO(
        start_time=datetime(2024, 12, 21, 23, 0, 0),
        adt=3 * 24.0,  # 3 days
        site_id=1,
    )

    result = calculator.calculate(holiday_input)

    closure_dates = {h.date for h in result.closure_holidays}
    weekend_dates = {h.date for h in result.weekend_holidays}
    working_holiday_dates = {h.date for h in result.working_holidays}

    assert date(2024, 12, 25) in closure_dates           # Christmas
    assert date(2024, 12, 21) in weekend_dates           # Saturday
    assert date(2024, 12, 22) in weekend_dates           # Sunday
    assert working_holiday_dates == set()                # No working holidays
    assert result.n_closure_days == 3


def test_holiday_calculation_all_enabled(populated_session):
    fake_connector = FakeReadOnlyDBConnector(populated_session)
    calculator = HolidayCalculator(
        consider_closure_holidays=True,
        consider_weekends_holidays=True,
        consider_working_holidays=True,
        maybe_ro_db_connector=fake_connector,
        maybe_days_window=10
    )

    holiday_input = HolidayADTInputDTO(
        start_time=datetime(2024, 12, 20),
        adt = 24 * 5,  # 5 days
        site_id=1,
    )

    result = calculator.calculate(holiday_input)

    closure_dates = {h.date for h in result.closure_holidays}
    weekend_dates = {h.date for h in result.weekend_holidays}
    working_holiday_dates = {h.date for h in result.working_holidays}

    assert date(2024, 12, 25) in closure_dates
    assert date(2024, 12, 21) in weekend_dates           # Saturday
    assert date(2024, 12, 22) in working_holiday_dates   # Working Sunday
    assert result.n_closure_days == 2

def test_holiday_retrieval_all_enabled(populated_session):
    fake_connector = FakeReadOnlyDBConnector(populated_session)
    calculator = HolidayCalculator(
        consider_closure_holidays=True,
        consider_working_holidays=False,
        consider_weekends_holidays=True,
        maybe_ro_db_connector=fake_connector,
        maybe_days_window=10
    )

    holiday_input = HolidayPeriodInputDTO(
        start_time=datetime(2024, 12, 21, 23, 0, 0),
        end_time=datetime(2024, 12, 25, 1, 0, 0),
        site_id=1,
    )

    result = calculator.calculate(holiday_input)

    closure_dates = {h.date for h in result.closure_holidays}
    weekend_dates = {h.date for h in result.weekend_holidays}
    working_holiday_dates = {h.date for h in result.working_holidays}

    assert date(2024, 12, 25) in closure_dates           # Christmas
    assert date(2024, 12, 21) in weekend_dates           # Saturday
    assert date(2024, 12, 22) in weekend_dates           # Sunday
    assert working_holiday_dates == set()                # No working holidays
    assert result.n_closure_days == 3



def test_holiday_retrieval_no_holidays_found(in_memory_session):
    country = Country(
        code="YY",
        name="Nowhereland",
        total_holidays=0,
        weekend_start=6,
        weekend_end=7
    )
    location = Location(name="Ghost Town", country=country, city="Ghost City", state="Ghost State", latitude=0.0, longitude=0.0)
    supplier = Supplier(name="Ghost Supplier", manufacturer_supplier_id="GS123")
    site = Site(
        id=2,
        location=location,
        supplier=supplier,
        consider_closure_holidays=True,
        consider_weekends_holidays=True,
        consider_working_holidays=True
    )
    in_memory_session.add_all([country, location, site])
    in_memory_session.commit()

    fake_connector = FakeReadOnlyDBConnector(in_memory_session)
    calculator = HolidayCalculator(
        consider_closure_holidays=True,
        consider_working_holidays=True,
        consider_weekends_holidays=False,
        maybe_ro_db_connector=fake_connector,
        maybe_days_window=10
    )

    holiday_input = HolidayPeriodInputDTO(
        start_time=datetime(2024, 11, 1),
        end_time=datetime(2024, 11, 10),
        site_id=2,
        
    )

    result = calculator.calculate(holiday_input)

    assert result.n_closure_days == 0
    assert result.closure_holidays == []
    assert result.weekend_holidays == []
    assert result.working_holidays == []

def test_holiday_calculation_no_holidays_found(in_memory_session):
    country = Country(
        code="YY",
        name="Nowhereland",
        total_holidays=0,
        weekend_start=6,
        weekend_end=7
    )
    location = Location(name="Ghost Town", country=country, city="Ghost City", state="Ghost State", latitude=0.0, longitude=0.0)
    supplier = Supplier(name="Ghost Supplier", manufacturer_supplier_id="GS123")
    site = Site(
        id=2,
        location=location,
        supplier=supplier,
        consider_closure_holidays=True,
        consider_weekends_holidays=True,
        consider_working_holidays=True
    )
    in_memory_session.add_all([country, location, site])
    in_memory_session.commit()

    fake_connector = FakeReadOnlyDBConnector(in_memory_session)
    calculator = HolidayCalculator(
        consider_closure_holidays=True,
        consider_working_holidays=True,
        consider_weekends_holidays=False,
        maybe_ro_db_connector=fake_connector,
        maybe_days_window=10
    )

    holiday_input = HolidayADTInputDTO(
        start_time=datetime(2024, 11, 1),
        site_id=2,
        adt=48.0  # 2 days
    )

    result = calculator.calculate(holiday_input)

    assert result.n_closure_days == 0
    assert result.closure_holidays == []
    assert result.weekend_holidays == []
    assert result.working_holidays == []

