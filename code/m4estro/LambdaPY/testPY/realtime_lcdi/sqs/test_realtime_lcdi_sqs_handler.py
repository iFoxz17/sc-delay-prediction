import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from sqs.dto.sqs_event_dto import EventType
from sqs.dto.reconfiguration_dto import ReconfigurationEvent, DelayDTO, ExternalDisruptionDTO

from aws_lambda_powertools.utilities.typing import LambdaContext


@pytest.fixture
def sqs_event_payload():
    return {
        "Records": [
            {
                "body": json.dumps({
                    "event_type": "ORDER_EVENT",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "type_": "CARRIER_DELIVERY",
                        "tracking_number": "T123",
                        "event_location": "WH1"
                    }
                })
            }
        ]
    }

@patch("sqs.realtime_lcdi_sqs_handler.OrderEventHandler")
@patch("sqs.realtime_lcdi_sqs_handler.DisruptionEventHandler")
@patch("sqs.realtime_lcdi_sqs_handler.SCGraphResolver")
@patch("sqs.realtime_lcdi_sqs_handler.parse_as")
@patch("sqs.realtime_lcdi_sqs_handler.SqsClient")
def test_handler_order_event_with_sls_forwarded(
    mock_sqs_client,
    mock_parse_as,
    mock_vertex_resolver_cls,
    mock_disruption_handler_cls,
    mock_order_handler_cls,
    sqs_event_payload,
):
    # Mocks
    mock_order_handler = MagicMock()
    mock_order_handler.handle.return_value = [ReconfigurationEvent(
        orderId=1234,
        SLS=True,
        external=None,
        delay=None
    )]
    mock_order_handler_cls.return_value = mock_order_handler

    mock_vertex_resolver_cls.return_value = MagicMock()

    mock_parse_as.return_value = MagicMock(
        event_type=EventType.TRACKING_EVENT,
        data=MagicMock(),
        timestamp=datetime.now(timezone.utc)
    )

    # Patch global SQS client
    mock_sqs_client = MagicMock()
    mock_sqs_client.send_message.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "MessageId": "abc-123"
    }

    from sqs.realtime_lcdi_sqs_handler import handler
    handler(sqs_event_payload, context=LambdaContext())

    # Assertions
    mock_parse_as.assert_called_once()
    mock_order_handler.handle.assert_called_once()



@patch("sqs.realtime_lcdi_sqs_handler.OrderEventHandler")
@patch("sqs.realtime_lcdi_sqs_handler.DisruptionEventHandler")
@patch("sqs.realtime_lcdi_sqs_handler.SCGraphResolver")
@patch("sqs.realtime_lcdi_sqs_handler.parse_as")
@patch("sqs.realtime_lcdi_sqs_handler.SqsClient")
def test_handler_order_event_with_delay_not_forwarded(
    mock_sqs_client,
    mock_parse_as,
    mock_vertex_resolver_cls,
    mock_disruption_handler_cls,
    mock_order_handler_cls,
    sqs_event_payload,
):
    # Mocks
    mock_order_handler = MagicMock()
    mock_order_handler.handle.return_value = [ReconfigurationEvent(
        orderId=1234,
        SLS=False,
        external=None,
        delay=DelayDTO(
            dispatch_lower=0.2,
            dispatch_upper=0.5,
            shipment_lower=-1.2,
            shipment_upper=-0.5,
            expected_order_delivery_time=datetime.now(timezone.utc),
            estimated_order_delivery_time=datetime.now(timezone.utc) + timedelta(hours=1.0)
        )
    )]
    mock_order_handler_cls.return_value = mock_order_handler

    mock_vertex_resolver_cls.return_value = MagicMock()

    mock_parse_as.return_value = MagicMock(
        event_type=EventType.TRACKING_EVENT,
        data=MagicMock(),
        timestamp=datetime.now(timezone.utc)
    )

    # Patch global SQS client
    mock_sqs_client = MagicMock()
    mock_sqs_client.send_message.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "MessageId": "abc-123"
    }

    from sqs.realtime_lcdi_sqs_handler import handler
    handler(sqs_event_payload, context=LambdaContext())

    # Assertions
    mock_parse_as.assert_called_once()
    mock_order_handler.handle.assert_called_once()
    mock_sqs_client.assert_not_called()

@patch("sqs.realtime_lcdi_sqs_handler.OrderEventHandler")
@patch("sqs.realtime_lcdi_sqs_handler.DisruptionEventHandler")
@patch("sqs.realtime_lcdi_sqs_handler.SCGraphResolver")
@patch("sqs.realtime_lcdi_sqs_handler.parse_as")
@patch("sqs.realtime_lcdi_sqs_handler.SqsClient")
def test_handler_order_event_with_delay_forwarded(
    mock_sqs_client,
    mock_parse_as,
    mock_vertex_resolver_cls,
    mock_disruption_handler_cls,
    mock_order_handler_cls,
    sqs_event_payload,
):
    # Mocks
    mock_order_handler = MagicMock()
    mock_order_handler.handle.return_value = [ReconfigurationEvent(
        orderId=1234,
        SLS=False,
        external=None,
        delay=DelayDTO(
            dispatch_lower=-0.2,
            dispatch_upper=-0.5,
            shipment_lower=1.2,
            shipment_upper=1.5,
            expected_order_delivery_time=datetime.now(timezone.utc),
            estimated_order_delivery_time=datetime.now(timezone.utc) + timedelta(hours=2.0)
        )
    )]
    mock_order_handler_cls.return_value = mock_order_handler

    mock_vertex_resolver_cls.return_value = MagicMock()

    mock_parse_as.return_value = MagicMock(
        event_type=EventType.TRACKING_EVENT,
        data=MagicMock(),
        timestamp=datetime.now(timezone.utc)
    )

    # Patch global SQS client
    mock_sqs_client = MagicMock()
    mock_sqs_client.send_message.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "MessageId": "abc-123"
    }

    from sqs.realtime_lcdi_sqs_handler import handler
    handler(sqs_event_payload, context=LambdaContext())

    # Assertions
    mock_parse_as.assert_called_once()
    mock_order_handler.handle.assert_called_once()

@patch("sqs.realtime_lcdi_sqs_handler.OrderEventHandler")
@patch("sqs.realtime_lcdi_sqs_handler.DisruptionEventHandler")
@patch("sqs.realtime_lcdi_sqs_handler.SCGraphResolver")
@patch("sqs.realtime_lcdi_sqs_handler.parse_as")
@patch("sqs.realtime_lcdi_sqs_handler.SqsClient")
def test_handler_order_event_with_external_disruption_forwarded(
    mock_sqs_client,
    mock_parse_as,
    mock_vertex_resolver_cls,
    mock_disruption_handler_cls,
    mock_order_handler_cls,
    sqs_event_payload,
):
    # Mocks
    mock_order_handler = MagicMock()
    mock_order_handler.handle.return_value = [ReconfigurationEvent(
        orderId=1234,
        SLS=False,
        external=ExternalDisruptionDTO(
            disruptionType="NAIVE",
            severity=0.1
        ),
        delay=None
    )]
    mock_order_handler_cls.return_value = mock_order_handler

    mock_vertex_resolver_cls.return_value = MagicMock()

    mock_parse_as.return_value = MagicMock(
        event_type=EventType.TRACKING_EVENT,
        data=MagicMock(),
        timestamp=datetime.now(timezone.utc)
    )

    # Patch global SQS client
    mock_sqs_client = MagicMock()
    mock_sqs_client.send_message.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "MessageId": "abc-123"
    }

    from sqs.realtime_lcdi_sqs_handler import handler
    handler(sqs_event_payload, context=LambdaContext())

    # Assertions
    mock_parse_as.assert_called_once()
    mock_order_handler.handle.assert_called_once()
