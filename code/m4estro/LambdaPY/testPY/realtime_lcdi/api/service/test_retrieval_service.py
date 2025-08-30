import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from api.service.retrieval_service import get_realtime_lcdi_by_order
from api.service.retrieval_service import RealtimeQParamKeys

from model.order import OrderStatus
from model.order import Order
from model.site import Site
from model.vertex import VertexType
from model.carrier import Carrier
from model.manufacturer import Manufacturer
from model.location import Location
from model.supplier import Supplier
from model.time_deviation import TimeDeviation
from model.alpha import Alpha
from model.estimated_time import EstimatedTime
from model.estimation_params import EstimationParams

@pytest.fixture
def fake_estimated_time():
    carrier = Carrier(id=1, name="DHL")
    location = Location(name="Warehouse A")
    supplier = Supplier(id=10, manufacturer_supplier_id=1001, name="ABC Supplies")
    site = Site(id=2, location=location, supplier=supplier)
    manufacturer = Manufacturer(id=3, name="XYZ Manufacturing", location=Location(name="Factory B"))
    order = Order(
        id=42,
        manufacturer_order_id=1000,
        tracking_number="TRACK123",
        carrier=carrier,
        site=site,
        manufacturer=manufacturer,
        SLS=True,
        SRS=False,
        status=OrderStatus.IN_TRANSIT.value,
        manufacturer_creation_timestamp=datetime(2023, 5, 1)
    )
    td = TimeDeviation(
        dt_confidence=0.8,
        st_confidence=0.9,
        dt_hours_lower=5,
        dt_hours_upper=10,
        st_hours_lower=2,
        st_hours_upper=4
    )
    alpha = Alpha(tt_weight=0.3, input=0.5, value=0.6)

    estimation_params = EstimationParams(
        dt_confidence=0.8,
        consider_closure_holidays=True,
        consider_working_holidays=False,
        consider_weekends_holidays=True,
        rte_mape=0.1,
        use_traffic_service=True,
        tmi_max_timediff_hours=1.0,
        use_weather_service=True,
        wmi_max_timediff_hours=2.0,
        wmi_step_distance_km=5.0,
        wmi_max_points=10,
        pt_path_min_prob=0.05,
        pt_max_paths=3,
        pt_ext_data_min_prob=0.1,
        pt_confidence=0.95,
        tt_confidence=0.9
    )        
        
    return EstimatedTime(
        order_id=order.id,
        order=order,
        vertex=MagicMock(id=999, name="Vertex A", type=VertexType.MANUFACTURER),
        estimation_time=datetime(2023, 5, 5),
        shipment_time=datetime(2023, 5, 3),
        event_time=datetime(2023, 5, 4),
        alpha=alpha,
        time_deviation=td,
        estimation_params=estimation_params,
        PT_avg_tmi=12.5,
        PT_avg_wmi=3.4,
        DT_lower=10.0,
        DT_upper=15.0,
        TT_lower=8.0,
        TT_upper=12.0,
        PT_n_paths=2,
        PT_lower=4.0,
        PT_upper=6.0,
        TFST_lower=7.0,
        TFST_upper=9.0,
        EST=13.5,
        EODT=15.2,
        CFDI_lower=1.1,
        CFDI_upper=1.9,
        EDD=datetime(2023, 5, 10)
    )

@patch("api.service.retrieval_service.get_read_only_db_connector")
@patch("api.service.retrieval_service.Formatter")
def test_get_realtime_lcdi_with_single_order(mock_formatter_cls, mock_get_db_connector, fake_estimated_time):
    mock_session = MagicMock()
    mock_connector = MagicMock()
    mock_connector.session_scope.return_value.__enter__.return_value = mock_session
    mock_get_db_connector.return_value = mock_connector

    # Provide one order's worth of data
    mock_session.query.return_value.options.return_value.filter.return_value.all.return_value = [fake_estimated_time]
    
    mock_formatter = MagicMock()
    mock_formatter_cls.return_value = mock_formatter
    mock_formatter.format_et_by_order.return_value = {"formatted": "data"}

    result = get_realtime_lcdi_by_order({
        RealtimeQParamKeys.ORDER.value: str(fake_estimated_time.order_id)
    })

    assert result == {"formatted": "data"}
    mock_formatter.format_et_by_order.assert_called_once()
    mock_session.query.assert_called()
