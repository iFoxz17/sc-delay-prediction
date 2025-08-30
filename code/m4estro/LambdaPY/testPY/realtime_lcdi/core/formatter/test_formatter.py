import pytest
from unittest.mock import Mock
from datetime import datetime
from types import SimpleNamespace

import igraph as ig

from model.vertex import VertexType
from model.order import OrderStatus
from model.alpha import Alpha, AlphaType

from graph_config import V_ID_ATTR, TYPE_ATTR

from core.query_handler.params.params_result import PTParams, TMIParams, TMISpeedParameters, TMIDistanceParameters, WMIParams, RTEstimatorParams

from core.executor.tfst_executor import TFSTCompute

from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.dt.holiday.holiday_dto import HolidayResultDTO
from core.calculator.tfst.pt.pt_dto import PT_DTO

from core.formatter.formatter import Formatter, EstimatedTimeSharedDTO

def test_format_et():
    alpha: Alpha = Alpha(
        type=AlphaType.EXP,
        tt_weight=0.5,
        tau=0.3,
        input=0.4,
        value=0.6
    )
    
    et = Mock()
    et.vertex_id = 1
    et.vertex.name = "Node A"
    et.vertex.type = VertexType.SUPPLIER_SITE

    et.order.manufacturer_creation_timestamp = datetime(2024, 5, 1)
    et.shipment_time = datetime(2024, 5, 2)
    et.event_time = datetime(2024, 5, 3)
    et.estimation_time = datetime(2024, 5, 4)
    et.status = OrderStatus.PENDING.value
    
    et.rte_mape = 0.15
    et.pt_confidence = 0.9
    et.tt_confidence = 0.8
    et.alpha = alpha
    et.consider_closure_holidays = True
    et.consider_working_holidays = False
    et.consider_weekends_holidays = True

    et.time_deviation.dt_confidence = 0.75
    et.time_deviation.st_confidence = 0.65
    et.PT_avg_tmi = 20.0
    et.PT_avg_wmi = 10.0
    et.DT_weekend_days = 2
    et.DT = 4.5
    et.TT_lower = 3.0
    et.TT_upper = 6.0
    et.PT_n_paths = 2
    et.PT_lower = 1.5
    et.PT_upper = 5.0
    et.TFST_lower = 0.5
    et.TFST_upper = 1.5
    et.EST = 2.0
    et.EODT = 5.2
    et.CFDI_lower = 1.0
    et.CFDI_upper = 2.0
    et.EDD = datetime(2024, 5, 10)

    et.time_deviation.dt_hours_lower = 1.0
    et.time_deviation.dt_hours_upper = 2.0
    et.time_deviation.st_hours_lower = 0.5
    et.time_deviation.st_hours_upper = 1.5

    et.order.id = 123
    et.order.manufacturer_order_id = 456
    et.order.tracking_number = "TRACK123"
    et.order.SLS = True
    et.order.SRS = False
    et.order.site.id = 1
    et.order.site.location.name = "Berlin"
    et.order.site.supplier.id = 11
    et.order.site.supplier.manufacturer_supplier_id = 22
    et.order.site.supplier.name = "Acme Co."
    et.order.carrier_id = 99
    et.order.carrier.name = "FastTrack"

    et.holidays = []

    formatter = Formatter()
    formatted = formatter.format_et(et)

    assert formatted["vertex"]["id"] == 1
    assert formatted["order"]["tracking_number"] == "TRACK123"
    assert formatted["site"]["location"] == "Berlin"
    assert formatted["supplier"]["name"] == "Acme Co."
    assert formatted["carrier"]["name"] == "FastTrack"
    assert formatted["indicators"]["delay"]["total"]["upper"] == 3.5


def test_format_et_by_order():
    shared = EstimatedTimeSharedDTO(
        order_id=1,
        manufacturer_order_id=2,
        tracking_number="T123",
        carrier_id=3,
        carrier_name="DHL",
        site_id=4,
        site_location="Munich",
        supplier_id=5,
        manufacturer_supplier_id=6,
        supplier_name="Global Supplies",
        manufacturer_id=7,
        manufacturer_name="Tech Corp",
        manufacturer_location="Berlin",
        SLS=True,
        SRS=False,
        EODT=12.5,
        EDD=datetime(2025, 1, 1),
        dispatch_td_lower=1.0,
        dispatch_td_upper=2.0,
        shipment_td_lower=0.5,
        shipment_td_upper=1.5,
        status="IN_TRANSIT"
    )

    alpha: Alpha = Alpha(
        type=AlphaType.EXP,
        tt_weight=0.5,
        tau=0.3,
        input=0.4,
        value=0.6
    )

    et = Mock()
    et.vertex_id = 99
    et.vertex.name = "Warehouse"
    et.vertex.type = VertexType.INTERMEDIATE
    et.order.manufacturer_creation_timestamp = datetime(2024, 1, 1)
    et.shipment_time = et.event_time = et.estimation_time = datetime(2024, 1, 2)
    et.status = "DELIVERED"
    et.consider_closure_holidays = True
    et.consider_working_holidays = False
    et.consider_weekends_holidays = True
    et.rte_mape = et.pt_confidence = et.tt_confidence = 0.0
    et.alpha = alpha
    et.time_deviation.dt_confidence = et.time_deviation.st_confidence = 0.0
    et.PT_avg_tmi = et.PT_avg_wmi = et.DT = 0.0
    et.TT_lower = et.TT_upper = et.PT_lower = et.PT_upper = 0.0
    et.PT_n_paths = 1
    et.TFST_lower = et.TFST_upper = et.EST = et.EODT = 0.0
    et.CFDI_lower = et.CFDI_upper = 0.0
    et.EDD = datetime(2024, 2, 2)
    et.time_deviation.dt_hours_lower = et.time_deviation.dt_hours_upper = 0.0
    et.time_deviation.st_hours_lower = et.time_deviation.st_hours_upper = 0.0

    et.holidays = []

    formatter = Formatter()
    formatted = formatter.format_et_by_order(shared, [et])

    assert formatted["order_id"] == 1
    assert formatted["site"]["location"] == "Munich"
    assert formatted["supplier"]["name"] == "Global Supplies"
    assert len(formatted["data"]) == 1
    assert formatted["delay"]["total"]["upper"] == 3.5


def test_format_volatile_result():
    vertex = ig.Graph().add_vertex(name="Hub", **{
        V_ID_ATTR: 42,
        TYPE_ATTR: VertexType.SUPPLIER_SITE.value
    })

    site = SimpleNamespace(id=1, location_name="Paris")
    supplier = SimpleNamespace(id=2, manufacturer_supplier_id=3, name="Best Supplies")
    carrier = SimpleNamespace(id=4, name="Speedy Carrier")
    manufacturer = SimpleNamespace(id=5, name="Tech Corp", location_name="Berlin")

    executor_result = SimpleNamespace(
        time_sequence=SimpleNamespace(
            order_time=datetime(2025, 1, 1),
            shipment_time=datetime(2025, 1, 2),
            event_time=datetime(2025, 1, 3),
            estimation_time=datetime(2025, 1, 4)
        ),
        tfst_executor_result=SimpleNamespace(
            pt=PT_DTO(
                avg_tmi=11.0,
                avg_wmi=9.0,
                lower=1.0,
                upper=3.0,
                n_paths=2,
                params=PTParams(
                    rte_estimator_params= RTEstimatorParams(model_mape=0.1, use_model=True),
                    tmi_params=TMIParams(
                        speed_parameters=TMISpeedParameters.default(),
                        distance_parameters=TMIDistanceParameters.default(),
                        use_traffic_service=False,
                        traffic_max_timedelta=0.0
                    ),
                    wmi_params=WMIParams(
                        use_weather_service=False,
                        weather_max_timedelta=0.0,
                        step_distance_km=0.0,
                        max_points=0
                    ),
                    path_min_probability=0.5,
                    max_paths=10,
                    ext_data_min_probability=0.1,
                    confidence=0.95
                ),
                tmi_data=[],
                wmi_data=[]
            ),
            tt=SimpleNamespace(lower=3.5, upper=6.5, confidence=0.75),
            tfst=SimpleNamespace(lower=0.4, upper=1.4, tolerance=0.1, computed=TFSTCompute.ALL),
            alpha=SimpleNamespace(input=0.6, value=0.8, type_=AlphaType.EXP, maybe_tt_weight=0.9, maybe_tau=0.5),
        ),
        time_deviation=SimpleNamespace(
            dt_confidence=0.7,
            st_confidence=0.6,
            dt_td_lower=1.2,
            dt_td_upper=2.2,
            st_td_lower=0.8,
            st_td_upper=1.3
        ),
        dt=DT_DTO(
            confidence=0.95,
            elapsed_time=5.0,
            elapsed_working_time=4.0,
            elapsed_holidays=HolidayResultDTO(
                consider_closure_holidays=True,
                consider_working_holidays=False,
                consider_weekends_holidays=True,
                closure_holidays=[],
                working_holidays=[],
                weekend_holidays=[]
            ),
            remaining_time_lower=2.0,
            remaining_working_time_lower=1.5,
            remaining_time_upper=2.0,
            remaining_working_time_upper=1.5,
            remaining_time=2.0,
            remaining_working_time=1.5,
            remaining_holidays=HolidayResultDTO(
                consider_closure_holidays=True,
                consider_working_holidays=False,
                consider_weekends_holidays=True,
                closure_holidays=[],
                working_holidays=[],
                weekend_holidays=[]
            )
        ),
        est=SimpleNamespace(value=2.1),
        eodt=SimpleNamespace(value=5.5),
        cfdi=SimpleNamespace(lower=1.1, upper=2.1),
        edd=SimpleNamespace(value=datetime(2025, 1, 10))
    )

    alpha_opt = SimpleNamespace(tt_weight=0.9)

    formatter = Formatter()
    result = formatter.format_volatile_result(vertex, site, supplier, carrier, manufacturer, executor_result, status=OrderStatus.PENDING)      # type: ignore

    assert result["site"]["location"] == "Paris"
    assert result["supplier"]["name"] == "Best Supplies"
    assert result["carrier"]["name"] == "Speedy Carrier"
    assert result["manufacturer"]["name"] == "Tech Corp"
    assert result["vertex"]["id"] == 42
    assert result["status"] == OrderStatus.PENDING.value
    assert result["indicators"]["parameters"]["alpha"]["tt_weight"] == 0.9
    assert result["indicators"]["delay"]["total"]["upper"] == 3.5
    assert result["indicators"]["EDD"] == "2025-01-10T00:00:00"

