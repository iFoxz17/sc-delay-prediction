import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import List

from sqs.dto.reconfiguration_dto import ReconfigurationEvent
from sqs.handler.disruption_event_handler import DisruptionEventHandler
from resolver.vertex_resolver import VertexResolver

from sqs.dto.disruption_event_dto import (
    DisruptionEventDataDTO,
    DisruptionDTO,
    DisruptionLocationDTO,
    AffectedOrdersDTO,
    AffectedOrderSummaryDTO
)

@pytest.fixture
def sample_event_data() -> DisruptionEventDataDTO:
    return DisruptionEventDataDTO(
        eventTimestamp="2023-10-01T12:00:00Z",
        disruption=DisruptionDTO(
            disruptionType="TEST_TYPE",
            disruptionLocation=DisruptionLocationDTO(
                name="Factory-X",
                coordinates=[45.0, 7.0],
                radiusKm=3.5
            ),
            measurements={"severity": 0.8}
        ),
        affectedOrders=AffectedOrdersDTO(
            total=2,
            summary=AffectedOrderSummaryDTO(
                orderIds=[101, 102],
                statuses=["DELIVERED", "SHIPPED"],
                locations=["LOC_A", "LOC_B"]
            )
        )
    )

@pytest.fixture
def mock_sc_graph_resolver() -> VertexResolver:
    resolver = MagicMock(spec=VertexResolver)
    resolver.resolve.return_value.vertex = {"v_id": 999}
    resolver.resolve.return_value.sc_graph = MagicMock()
    return resolver

@patch("sqs.handler.disruption_event_handler.compute_order_realtime_lcdi")
@patch("sqs.handler.disruption_event_handler.get_read_only_db_connector")
def test_disruption_event_handler_returns_expected_events(
    db_connector_mock,
    compute_lcdi_mock,
    sample_event_data,
    mock_sc_graph_resolver,
):
    # Setup DB session mock
    session_mock = MagicMock()
    db_connector_mock.return_value.session_scope.return_value.__enter__.return_value = session_mock

    def get_order_by_id(order_id):
        mock_order = MagicMock()
        mock_order.id = order_id
        mock_order.status = "ACTIVE"
        mock_order.SLS = True
        return mock_order

    session_mock.get_order_by_id.side_effect = get_order_by_id

    # Setup mock result of LCDI computation
    now = datetime.now(timezone.utc)
    compute_lcdi_mock.return_value = {
        "order": {
            "id": 101,
            "SLS": True,
        },
        "indicators": {
            "EDD": now.isoformat(),
            "delay": {
                "dispatch": {"lower": 1.0, "upper": 1.5},
                "shipment": {"lower": 2.2, "upper": 3.2},
                "total": {"lower": 3.2, "upper": 4.7},
            },
        }
    }

    handler = DisruptionEventHandler(sc_graph_resolver=mock_sc_graph_resolver)
    timestamp = datetime.now(timezone.utc)

    result: List[ReconfigurationEvent] = handler.handle(sample_event_data, timestamp)

    assert len(result) == 2
    for event in result:
        assert isinstance(event, ReconfigurationEvent)
        assert event.order_id in [101, 102]
        assert event.delay is not None
        assert event.external is not None
        assert event.external.disruption_type == "TEST_TYPE"
        assert event.external.severity == 0.8
        assert event.sls is True
        assert event.delay.dispatch_lower == 1.0
        assert event.delay.shipment_upper == 3.2

    assert compute_lcdi_mock.call_count == 2
    assert db_connector_mock.called
