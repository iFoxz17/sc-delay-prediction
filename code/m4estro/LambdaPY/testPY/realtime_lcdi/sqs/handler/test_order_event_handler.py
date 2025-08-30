import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from sqs.handler.order_event_handler import OrderEventHandler
from sqs.dto.order_event_dto import OrderEventDataDTO, OrderEventType
from sqs.dto.reconfiguration_dto import ReconfigurationEvent, DelayDTO
from resolver.vertex_dto import VertexDTO
from core.sc_graph.sc_graph_resolver import SCGraphVertexResult
from model.vertex import VertexType
from graph_config import V_ID_ATTR, TYPE_ATTR


@pytest.fixture
def mock_order():
    mock = MagicMock()
    mock.id = 123
    mock.status = "SHIPPED"
    mock.site_id = 456
    mock.manufacturer.name = "AcmeCorp"
    return mock


@pytest.fixture
def mock_event_data():
    return OrderEventDataDTO(
        type=OrderEventType.CARRIER_UPDATE,
        orderId=123,
        trackingNumber="TRACK123",
        eventTimestamps=["2023-10-01T12:00:00Z", "2023-10-01T12:30:00Z"],
        orderNewStepsIds=[1, 2],
        orderNewLocations=["LocationA", "LocationB"]
    )


@pytest.fixture
def mock_sc_graph_resolver():
    return MagicMock()


@pytest.fixture
def handler(mock_sc_graph_resolver):
    return OrderEventHandler(sc_graph_resolver=mock_sc_graph_resolver())


@patch("sqs.handler.order_event_handler.get_read_only_db_connector")
@patch("sqs.handler.order_event_handler.compute_order_realtime_lcdi")
def test_handle_successful_carrier_update(
    mock_compute_lcdi,
    mock_get_db,
    handler,
    mock_event_data,
    mock_order,
    mock_sc_graph_resolver
):
    # Mock DB connector and session
    mock_session = MagicMock()
    mock_qh = MagicMock()
    mock_qh.get_order_by_tracking_number.return_value = mock_order
    mock_session_scope = MagicMock()
    mock_session_scope.__enter__.return_value = mock_session
    mock_session_scope.__exit__.return_value = None

    mock_get_db.return_value.session_scope.return_value = mock_session_scope
    mock_session.__enter__.return_value = mock_qh
    mock_session.__exit__.return_value = None
    mock_qh.get_order_by_tracking_number.return_value = mock_order

    # Mock vertex resolution
    mock_vertex = {
        V_ID_ATTR: "vtx-789",
        "name": "AcmeCorp",
        TYPE_ATTR: VertexType.MANUFACTURER
    }
    mock_sc_graph = MagicMock()  # Assuming SCGraph is a mockable object
    mock_vertex_result = SCGraphVertexResult(vertex=mock_vertex, sc_graph=mock_sc_graph)
    mock_sc_graph_resolver.resolve.return_value = mock_vertex_result

    # Mock LCDI computation
    mock_et_data = {"dummy": "value"}
    mock_compute_lcdi.return_value = mock_et_data

    expected_reconf = [
        ReconfigurationEvent(
            orderId=123,
            SLS=False,
            external=None,
            delay=DelayDTO(
                dispatch_lower=1.0,
                dispatch_upper=1.5,
                shipment_lower=2.2,
                shipment_upper=3.2,
                estimated_order_delivery_time=datetime.fromisoformat("2023-10-01T12:00:00Z"),
                expected_order_delivery_time=datetime.fromisoformat("2023-10-01T12:00:00Z") + timedelta(hours=2.5)
            )
        ),
        ReconfigurationEvent(
            orderId=123,
            SLS=False,
            external=None,
            delay=DelayDTO(
                dispatch_lower=1.3,
                dispatch_upper=1.7,
                shipment_lower=1.2,
                shipment_upper=6.7,
                estimated_order_delivery_time=datetime.fromisoformat("2023-10-02T12:00:00Z"),
                expected_order_delivery_time=datetime.fromisoformat("2023-10-02T12:00:00Z") + timedelta(hours=3.5)
            )
        )
    ]

    # Mock ReconfigurationEvent.from_et
    with patch("sqs.handler.order_event_handler.ReconfigurationEvent.from_et", side_effect=expected_reconf) as mock_from_et:
        mock_from_et.return_value = expected_reconf

        # Call handle
        timestamp = datetime.now(timezone.utc)
        result = handler.handle(mock_event_data, timestamp)

        # Assertions
        assert result == expected_reconf
        mock_compute_lcdi.assert_called()
        assert mock_compute_lcdi.call_count == len(expected_reconf)
        mock_from_et.assert_called()
        assert mock_from_et.call_count == len(expected_reconf)

@patch("sqs.handler.order_event_handler.get_read_only_db_connector")
@patch("sqs.handler.order_event_handler.compute_order_realtime_lcdi")
def test_handle_carrier_update_no_data(
    mock_compute_lcdi,
    mock_get_db,
    handler,
    mock_order,
    mock_sc_graph_resolver
):
    # Mock DB connector and session
    mock_session = MagicMock()
    mock_qh = MagicMock()
    mock_qh.get_order_by_tracking_number.return_value = mock_order
    mock_session_scope = MagicMock()
    mock_session_scope.__enter__.return_value = mock_session
    mock_session_scope.__exit__.return_value = None

    mock_get_db.return_value.session_scope.return_value = mock_session_scope
    mock_session.__enter__.return_value = mock_qh
    mock_session.__exit__.return_value = None
    mock_qh.get_order_by_tracking_number.return_value = mock_order

    # Mock vertex resolution
    mock_vertex = {
        V_ID_ATTR: "vtx-789",
        "name": "AcmeCorp",
        TYPE_ATTR: VertexType.MANUFACTURER
    }
    mock_sc_graph = MagicMock()  # Assuming SCGraph is a mockable object
    mock_vertex_result = SCGraphVertexResult(vertex=mock_vertex, sc_graph=mock_sc_graph)
    mock_sc_graph_resolver.resolve.return_value = mock_vertex_result

    # Mock LCDI computation
    mock_et_data = {"dummy": "value"}
    mock_compute_lcdi.return_value = mock_et_data

    expected_reconf = []

    event_data = OrderEventDataDTO(
        type=OrderEventType.CARRIER_UPDATE,
        orderId=123,
        trackingNumber="TRACK123",
        eventTimestamps=[],
        orderNewStepsIds=[],
        orderNewLocations=[]
    )

    # Mock ReconfigurationEvent.from_et
    with patch("sqs.handler.order_event_handler.ReconfigurationEvent.from_et", return_value=expected_reconf) as mock_from_et:
        mock_from_et.return_value = expected_reconf

        # Call handle
        timestamp = datetime.now(timezone.utc)
        result = handler.handle(event_data, timestamp)

        # Assertions
        assert result == expected_reconf
        assert mock_compute_lcdi.call_count == 0
        assert mock_from_et.call_count == 0
