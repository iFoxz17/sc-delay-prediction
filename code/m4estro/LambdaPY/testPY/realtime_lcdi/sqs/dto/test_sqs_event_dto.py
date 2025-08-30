import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from sqs.dto.order_event_dto import OrderEventDataDTO
from sqs.dto.disruption_event_dto import DisruptionEventDataDTO, DisruptionDTO, AffectedOrdersDTO
from sqs.dto.sqs_event_dto import SqsEvent, EventType, SqsEventDataDTO

def test_parse_carrier_event():
    order_event_json = {
        "eventType": EventType.TRACKING_EVENT.value,
        "timestamp": "2025-05-14T09:15:23.456Z",
        "data": {
            "type": "CARRIER_UPDATE",
            "orderId": 1,
            "trackingNumber": "1Z999AA123456789",
            "eventTimestamps": ["2025-05-14T09:10:23Z", "2025-05-14T09:12:00Z"],
            "orderNewStepsIds": [1, 2],
            "orderNewLocations": ["Leipzig, DE", "Berlin, DE"],
        }
    }

    event: SqsEvent = SqsEvent.model_validate(order_event_json)
    assert event.event_type == EventType.TRACKING_EVENT
    order_data: SqsEventDataDTO = event.data
    assert isinstance(order_data, OrderEventDataDTO)
    assert order_data.type_ == "CARRIER_UPDATE"
    assert order_data.order_id == 1
    assert order_data.tracking_number == "1Z999AA123456789"
    assert order_data.event_timestamps == ["2025-05-14T09:10:23Z", "2025-05-14T09:12:00Z"]
    assert order_data.order_new_steps_ids == [1, 2]
    assert order_data.order_new_locations == ["Leipzig, DE", "Berlin, DE"]
    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo == timezone.utc


def test_parse_disruption_event():
    disruption_event_json = {
        "eventType": "DISRUPTION_EVENT",
        "timestamp": "2025-05-14T09:15:23.456Z",
        "data": {
            "eventTimestamp": "2025-05-14T09:15:23.456Z",
            "disruption": {
                "disruptionType": "wildfire",
                "disruptionLocation": {
                    "name": "Leipzig, Germany",
                    "coordinates": [12.3731, 51.3397],
                    "radiusKm": 50
                },
                "measurements": {
                    "severity": 0.73
                }
            },
            "affectedOrders": {
                "total": 4,
                "summary": {
                    "orderIds": [12345, 67890, 11111, 22222],
                    "statuses": ["IN_TRANSIT", "IN_TRANSIT", "IN_TRANSIT", "IN_TRANSIT"],
                    "locations": [
                        "Frankfurt, Germany",
                        "Berlin, Germany",
                        "Hamburg, Germany",
                        "Dresden, Germany"
                    ]
                }
            }
        }
    }

    event: SqsEvent = SqsEvent.model_validate(disruption_event_json)
    assert event.event_type == EventType.DISRUPTION_ALERT
    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo == timezone.utc
    disruption_data: SqsEventDataDTO = event.data
    assert isinstance(disruption_data, DisruptionEventDataDTO)

    disruption: DisruptionDTO = disruption_data.disruption

    assert disruption.disruption_type == "wildfire"
    assert disruption.disruption_location.name == "Leipzig, Germany"
    assert disruption.disruption_location.coordinates == [12.3731, 51.3397]
    assert disruption.disruption_location.radius_km == 50
    assert disruption.measurements["severity"] == 0.73

    orders: AffectedOrdersDTO = disruption_data.affected_orders
    assert orders.total == 4
    assert orders.summary.order_ids == [12345, 67890, 11111, 22222]
    assert orders.summary.statuses == ["IN_TRANSIT"] * 4
    assert orders.summary.locations == [
        "Frankfurt, Germany",
        "Berlin, Germany",
        "Hamburg, Germany",
        "Dresden, Germany"
    ]


def test_invalid_event_type():
    invalid_event_json = {
        "eventType": "CARRIER_EVENT",  # invalid top-level event type
        "timestamp": "2025-05-14T09:15:23.456Z",
        "data": {
            "type": "ORDER_CREATION",
            "trackingNumber": "1Z999AA123456789",
            "eventLocation": "Frankfurt, DE"
        }
    }

    with pytest.raises(ValidationError):
        SqsEvent.model_validate(invalid_event_json)
