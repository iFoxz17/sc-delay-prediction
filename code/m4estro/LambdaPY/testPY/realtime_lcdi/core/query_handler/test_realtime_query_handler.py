import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model.alpha import Alpha
from model.alpha_opt import AlphaOpt
from model.country import Country
from model.location import Location
from model.order import Order
from model.site import Site
from model.supplier import Supplier
from model.carrier import Carrier
from model.shipment_time_gamma import ShipmentTimeGamma
from model.shipment_time_sample import ShipmentTimeSample
from model.shipment_time import ShipmentTime
from model.dispatch_time_gamma import DispatchTimeGamma
from model.dispatch_time_sample import DispatchTimeSample
from model.estimated_time import EstimatedTime
from model.tmi import TMI
from model.wmi import WMI

from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.dt.holiday.holiday_dto import HolidayResultDTO
from core.executor.executor import ExecutorResult, TimeSequenceDTO
from core.query_handler.params.params_result import PTParams, TMIParams, WMIParams, TMISpeedParameters, TMIDistanceParameters
from core.query_handler.query_handler import QueryHandler

@pytest.fixture(scope="function")
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # Assuming you have a Base metadata that includes all your models:
    from model.base import Base
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()

@pytest.fixture
def seeded_session(session):
    # Countries
    country = Country(id=1, name="TestCountry", code="TC", total_holidays=10, weekend_start=6, weekend_end=7)

    session.add(country)
    session.commit()

    # Locations
    location = Location(name="TestLocation", city="TestCity", state="TestState",
                        country_code="TC", latitude=12.34, longitude=56.78)

    session.add(location)
    session.commit()

    # Supplier
    supplier = Supplier(id=1, name="TestSupplier", manufacturer_supplier_id=12345)

    session.add(supplier)
    session.commit()

    # Sites
    site1 = Site(id=100, supplier_id=1, location_name="LocationA", n_rejections=0, n_orders=10)

    carrier1 = Carrier(id=1000, name="TestCarrier", carrier_17track_id="CARRIER123",
                       n_losses=0, n_orders=5)

    session.add_all([site1, carrier1])
    session.commit()

    # Order
    order = Order(id=1, manufacturer_id=10, site_id=100, carrier_id=1000, status="PENDING", n_steps=1, 
                  tracking_number="TRACK123", tracking_link="http://tracking.link/123",
                  manufacturer_creation_timestamp=datetime.now(timezone.utc),
                  manufacturer_estimated_delivery_timestamp=None,
                  manufacturer_confirmed_delivery_timestamp=None,
                  carrier_creation_timestamp=None,
                  carrier_estimated_delivery_timestamp=None,
                  carrier_confirmed_delivery_timestamp=None,
                  SLS=False)
    session.add(order)
    session.commit()

    # AlphaOpt
    alpha_opt = AlphaOpt(site_id=100, carrier_id=1000, tt_weight=0.5)
    session.add(alpha_opt)

    # DeliveryTimeGamma (for site_id=100, carrier_id=1000)
    dt_gamma = ShipmentTimeGamma(site_id=100, carrier_id=1000, shape=2.0, scale=1.5, loc=0.0,
                                 skewness=0.1, kurtosis=0.2, mean=3.0, std_dev=0.5, n=100)
    session.add(dt_gamma)

    # DeliveryTimeSample + DeliveryTime entries (for site_id=200, carrier_id=2000)
    dt_sample = ShipmentTimeSample(site_id=200, carrier_id=2000, median=6.5, mean=7.0, std_dev=1.0, n=50)
    session.add(dt_sample)
    dt_hours = [5.0, 6.5, 7.0]
    delivery_times = [
        ShipmentTime(site_id=200, carrier_id=2000, hours=h)
        for h in dt_hours
    ]
    session.add_all(delivery_times)

    # DispatchTimeGamma (for site_id=100)
    dispatch_gamma = DispatchTimeGamma(site_id=100, shape=1.7, scale=0.8, loc=0.0,
                                       skewness=0.1, kurtosis=0.2, mean=2.5, std_dev=0.3, n=50)
    session.add(dispatch_gamma)

    # DispatchTimeSample (for site_id=200)
    dispatch_sample = DispatchTimeSample(site_id=200, median=4.5, mean=5.0, std_dev=0.8, n=30)
    session.add(dispatch_sample)

    session.commit()
    return session

def test_get_order(seeded_session):
    handler = QueryHandler(seeded_session)
    order = handler.get_order(1)
    assert order.id == 1
    assert order.site_id == 100
    assert order.carrier_id == 1000

def test_get_site(seeded_session):
    handler = QueryHandler(seeded_session)
    site = handler.get_site(100)
    assert site.id == 100
    assert site.location_name == "LocationA"
    assert site.supplier_id == 1

def test_get_carrier(seeded_session):
    handler = QueryHandler(seeded_session)
    carrier = handler.get_carrier(1000)
    assert carrier.id == 1000
    assert carrier.name == "TestCarrier"
    assert carrier.carrier_17track_id == "CARRIER123"

def test_get_carrier_by_name(seeded_session):
    handler = QueryHandler(seeded_session)
    carrier = handler.get_carrier_by_name("TestCarrier")
    assert carrier.id == 1000
    assert carrier.name == "TestCarrier"
    assert carrier.carrier_17track_id == "CARRIER123"

def test_get_alpha_opt(seeded_session):
    handler = QueryHandler(seeded_session)
    opt = handler.get_alpha_opt(100, 1000)
    assert opt.tt_weight == 0.5

def test_get_delivery_time_gamma(seeded_session):
    handler = QueryHandler(seeded_session)
    result = handler.get_delivery_time(100, 1000)
    assert hasattr(result, "dt_gamma")
    assert result.dt_gamma.shape == 2.0             # type: ignore
    assert result.dt_gamma.scale == 1.5             # type: ignore

def test_get_delivery_time_sample(seeded_session):
    handler = QueryHandler(seeded_session)
    result = handler.get_delivery_time(200, 2000)
    assert hasattr(result, "dt_sample")
    assert isinstance(result.dt_x, list)            # type: ignore  
    assert 6.5 in result.dt_x               # type: ignore  

def test_get_dispatch_time_gamma(seeded_session):
    handler = QueryHandler(seeded_session)
    result = handler.get_dispatch_time(100)
    assert hasattr(result, "dt_gamma")
    assert result.dt_gamma.shape == 1.7             # type: ignore

def test_get_dispatch_time_sample(seeded_session):
    handler = QueryHandler(seeded_session)
    result = handler.get_dispatch_time(200)
    assert hasattr(result, "dt_sample")

def test_save_estimated_time(seeded_session):
    handler = QueryHandler(seeded_session)
    now = datetime.now(timezone.utc)

    class DummyValue:
        def __init__(self, value):
            self.value = value
        def __float__(self):
            return float(self.value)

    class DummyAlpha:
        def __init__(self):
            self.type_ = "EXP"
            self.maybe_tt_weight = 0.1
            self.maybe_tau = 0.5
            self.maybe_gamma = None
            self.input = 1.0
            self.value = 0.8

    class DummyTMI:
        def __init__(self):
            self.source_id = 1
            self.destination_id = 2
            self.timestamp = now
            self.transportation_mode = "ROAD"
            self.value = 1.0

    class DummyWMI:
        def __init__(self):
            self.source_id = 1
            self.destination_id = 2
            self.timestamp = now
            self.n_interpolation_points = 5
            self.step_distance_km = 10.0
            self.value = 1.0

    class DummyPT:
        def __init__(self):
            self.n_paths = 2
            self.avg_tmi = 1.15
            self.avg_wmi = 1.25
            self.lower = 1.0
            self.upper = 2.0

            self.tmi_data = [DummyTMI(), DummyTMI()]
            self.wmi_data = [DummyWMI(), DummyWMI(), DummyWMI()]

            self.params = PTParams(
                path_min_probability=0.1,
                max_paths=5,
                ext_data_min_probability=0.05,
                confidence=0.95,
                rte_estimator_params=MagicMock(model_mape=0.15, use_model=True),
                wmi_params=MagicMock(
                    use_weather_service=True,
                    wmi_max_timediff=2.0,
                    step_distance_km=10.0,
                    max_points=100.0
                ),
                tmi_params=MagicMock(
                    use_traffic_service=True,
                    traffic_max_timedelta=2.0,
                    speed_params=TMISpeedParameters.default(),
                    distance_params=TMIDistanceParameters.default()
                )
            )

    class DummyTT:
        def __init__(self):
            self.lower = 3.0
            self.upper = 4.0
            self.confidence = 0.9

    class DummyTFST:
        def __init__(self):
            self.lower = 0.5
            self.upper = 0.7
            self.tolerance = 0.1

    class DummyCFDI:
        def __init__(self):
            self.lower = 0.1
            self.upper = 0.9

    class DummyTimeDeviation:
        def __init__(self):
            self.dt_td_lower = 1.0
            self.dt_td_upper = 1.0
            self.st_td_lower = 2.0
            self.st_td_upper = 3.0
            self.dt_confidence = 0.95
            self.st_confidence = 0.9

    class DummyTFSTExecutorResult:
        def __init__(self):
            self.alpha = DummyAlpha()
            self.pt = DummyPT()
            self.tt = DummyTT()
            self.tfst = DummyTFST()

    tfst_executor_result = DummyTFSTExecutorResult()

    # Make HolidayResultDTO with total_time and total_holidays for DT_DTO
    holidays_dto = HolidayResultDTO(
        consider_closure_holidays=True,
        consider_working_holidays=False,
        consider_weekends_holidays=True,
        closure_holidays=[],
        working_holidays=[],
        weekend_holidays=[]
    )
    
    dt_dto = DT_DTO(
        confidence=0.95,
        elapsed_time=2.0,
        elapsed_working_time=1.5,
        elapsed_holidays=holidays_dto,
        remaining_time_lower=1.0,
        remaining_time=1.5,
        remaining_time_upper=2.0,
        remaining_working_time_lower=0.5,
        remaining_working_time=1.0,
        remaining_working_time_upper=1.0,
        remaining_holidays=holidays_dto,
    )
    
    executor_result = ExecutorResult(
        dt=dt_dto,
        est=DummyValue(1.0),                                                # type: ignore
        eodt=DummyValue(3.0),                                               # type: ignore                        
        edd=DummyValue(datetime(2025, 7, 1, tzinfo=timezone.utc)),          # type: ignore
        cfdi=DummyCFDI(),                                                   # type: ignore
        time_deviation=DummyTimeDeviation(),                                # type: ignore
        tfst_executor_result=tfst_executor_result,                          # type: ignore
        time_sequence=TimeSequenceDTO(
            order_time=now,
            shipment_time=now + timedelta(hours=1),
            event_time=now + timedelta(hours=2),
            estimation_time=now + timedelta(hours=3)
        )
    )

    alpha_opt = handler.get_alpha_opt(100, 1000)
    assert alpha_opt is not None

    et = handler.save_estimated_time(
        order_id=1,
        vertex_id=5,
        order_status="PENDING",
        executor_result=executor_result
    )

    et_id = et.id
    et = seeded_session.get(EstimatedTime, et_id)
    assert et is not None
    assert et.order_id == 1
    assert et.vertex_id == 5
    assert et.TFST_lower == 0.5
    assert et.DT_lower == 3.0
    assert et.DT_upper == 4.0
    assert et.EODT == 3.0
    #assert et.EDD == datetime(2025, 7, 1, tzinfo=timezone.utc)
    assert et.time_deviation_id is not None
    assert et.alpha_id is not None
    assert et.alpha.type.value == "EXP"
    assert et.alpha.tt_weight == 0.1
    assert et.alpha.tau == 0.5
    assert et.alpha.input == 1.0
    assert et.alpha.value == 0.8
    assert et.PT_n_paths == 2
    assert et.PT_avg_tmi == 1.15
    assert et.PT_avg_wmi == 1.25
    assert et.PT_lower == 1.0
    assert et.PT_upper == 2.0
    assert et.estimation_params.consider_closure_holidays is True
    assert et.estimation_params.consider_working_holidays is False
    assert et.estimation_params.consider_weekends_holidays is True
    assert et.estimation_params.pt_confidence == 0.95


    tmi_data = seeded_session.query(TMI).filter_by(estimated_time_id=et_id).all()
    assert len(tmi_data) == 2

    wmi_data = seeded_session.query(WMI).filter_by(estimated_time_id=et_id).all()
    assert len(wmi_data) == 3


from model.param import Base, Param, ParamName, ParamGeneralCategory, ParamCategory
from model.alpha import AlphaType

from core.query_handler.params.params_handler import ParamsHandler
from core.query_handler.params.params_result import ParamsResult


@pytest.fixture(scope="function")
def populated_session(session):
    # Required parameters
    params = [
        # DT
        Param(name=ParamName.DT_CONFIDENCE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.DISPATCH_TIME.value, description="", value=0.95),
        # DT - Holidays
        Param(name=ParamName.CONSIDER_CLOSURE_HOLIDAYS.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.HOLIDAY.value, description="", value=1),
        Param(name=ParamName.CONSIDER_WORKING_HOLIDAYS.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.HOLIDAY.value, description="", value=0),
        Param(name=ParamName.CONSIDER_WEEKENDS_HOLIDAYS.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.HOLIDAY.value, description="", value=1),

        # TFST
        Param(name=ParamName.TFST_TOLERANCE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TFST.value, description="", value=0.1),

        # TFST - Alpha
        Param(name=ParamName.ALPHA_CONST_VALUE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.ALPHA.value, description="", value=0.8),
        Param(name=ParamName.ALPHA_CALCULATOR_TYPE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.ALPHA.value, description="", value=1),

        # TFST - PT
        Param(name=ParamName.PT_PATH_MIN_PROBABILITY.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.PT.value, description="", value=0.1),
        Param(name=ParamName.PT_MAX_PATHS.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.PT.value, description="", value=5),
        Param(name=ParamName.PT_EXT_DATA_MIN_PROBABILITY.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.PT.value, description="", value=0.05),
        Param(name=ParamName.PT_CONFIDENCE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.PT.value, description="", value=0.95),

        # TFST - TT
        Param(name=ParamName.TT_CONFIDENCE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TT.value, description="", value=0.9),

        # TFST - Route Estimator
        Param(name=ParamName.RT_ESTIMATOR_MODEL_MAPE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.ROUTE_TIME_ESTIMATOR.value, description="", value=0.15),
        Param(name=ParamName.RT_ESTIMATOR_USE_MODEL.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.ROUTE_TIME_ESTIMATOR.value, description="", value=1.0),

        # TFST - TMI Speed
        Param(name=ParamName.TMI_AIR_MIN_SPEED_KM_H.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=500.0),
        Param(name=ParamName.TMI_AIR_MAX_SPEED_KM_H.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=900.0),
        Param(name=ParamName.TMI_SEA_MIN_SPEED_KM_H.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=30.0),
        Param(name=ParamName.TMI_SEA_MAX_SPEED_KM_H.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=50.0),
        Param(name=ParamName.TMI_RAIL_MIN_SPEED_KM_H.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=60.0),
        Param(name=ParamName.TMI_RAIL_MAX_SPEED_KM_H.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=120.0),
        Param(name=ParamName.TMI_ROAD_MIN_SPEED_KM_H.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=70.0),
        Param(name=ParamName.TMI_ROAD_MAX_SPEED_KM_H.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=130.0),

        # TFST - TMI Distance
        Param(name=ParamName.TMI_AIR_MIN_DISTANCE_KM.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=100.0),
        Param(name=ParamName.TMI_AIR_MAX_DISTANCE_KM.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=10000.0),
        Param(name=ParamName.TMI_SEA_MIN_DISTANCE_KM.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=50.0),
        Param(name=ParamName.TMI_SEA_MAX_DISTANCE_KM.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=15000.0),
        Param(name=ParamName.TMI_RAIL_MIN_DISTANCE_KM.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=30.0),
        Param(name=ParamName.TMI_RAIL_MAX_DISTANCE_KM.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=5000.0),
        Param(name=ParamName.TMI_ROAD_MIN_DISTANCE_KM.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=10.0),
        Param(name=ParamName.TMI_ROAD_MAX_DISTANCE_KM.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=2000.0),
        Param(name=ParamName.TMI_USE_TRAFFIC_SERVICE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=1.0),
        Param(name=ParamName.TMI_TRAFFIC_MAX_TIMEDIFF.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.TMI.value, description="", value=3.0),

        # TFST - WMI
        Param(name=ParamName.WMI_USE_WEATHER_SERVICE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.WMI.value, description="", value=1.0),
        Param(name=ParamName.WMI_WEATHER_MAX_TIMEDIFF.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.WMI.value, description="", value=2.0),
        Param(name=ParamName.WMI_STEP_DISTANCE_KM.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.WMI.value, description="", value=10.0),
        Param(name=ParamName.WMI_MAX_POINTS.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.WMI.value, description="", value=100.0),

        # TIME_DEVIATION
        Param(name=ParamName.DELAY_DT_CONFIDENCE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.SYSTEM.value, description="", value=0.85),
        Param(name=ParamName.DELAY_ST_CONFIDENCE.value, general_category=ParamGeneralCategory.REALTIME.value, category=ParamCategory.SYSTEM.value, description="", value=0.9),

        # SYSTEM
        Param(name=ParamName.PARALLELIZATION.value, general_category=ParamGeneralCategory.SYSTEM.value, category=ParamCategory.SYSTEM.value, description="", value=4.0),
    ]

    session.add_all(params)
    session.commit()
    return session


def test_get_params_returns_complete_result(populated_session):
    handler = ParamsHandler(populated_session)
    result: ParamsResult = handler.get_params()

    assert result is not None
    assert result.dt_params is not None
    assert result.tfst_params is not None
    assert result.time_deviation_params is not None

    assert result.dt_params.confidence == 0.95
        
    assert result.parallelization == 4
    assert result.dt_params.holidays_params.consider_closure_holidays is True
    assert result.dt_params.holidays_params.consider_working_holidays is False
    assert result.dt_params.holidays_params.consider_weekends_holidays is True

    assert result.tfst_params.alpha_params.const_alpha_value == 0.8
    assert result.tfst_params.alpha_params.alpha_type == AlphaType.EXP
    assert result.tfst_params.pt_params.confidence == 0.95
    assert result.tfst_params.tt_params.confidence == 0.9

    assert result.time_deviation_params.dt_time_deviation_confidence == 0.85
    assert result.time_deviation_params.st_time_deviation_confidence == 0.9

    
