import pytest
from pydantic import ValidationError
from sqs.dto.reconfiguration_dto import ReconfigurationEvent

def test_reconfiguration_event_full_payload():
    payload = {
        "orderId": 1234,
        "SLS": False,
        "external": {
            "disruptionType": "wildfire",
            "severity": 0.73
        },
        "delay": {
            "dispatch_lower": 1.0,
            "dispatch_upper": 2.0,
            "shipment_lower": 3.5,
            "shipment_upper": 7.12,
            "expected_order_delivery_time": "2023-10-01T12:00:00Z",
            "estimated_order_delivery_time": "2023-10-01T14:00:00Z"
        }
    }

    dto = ReconfigurationEvent(**payload)

    assert dto.order_id == 1234
    assert dto.sls is False
    assert dto.external is not None
    assert dto.external.disruption_type == "wildfire"
    assert dto.external.severity == 0.73
    assert dto.delay is not None
    assert dto.delay.dispatch_lower == 1.0
    assert dto.delay.dispatch_upper == 2.0
    assert dto.delay.shipment_lower == 3.5
    assert dto.delay.shipment_upper == 7.12
    assert pytest.approx(dto.delay.total_lower) == 4.5
    assert pytest.approx(dto.delay.total_upper) == 9.12

def test_reconfiguration_event_with_external_only():
    payload = {
        "orderId": 9999,
        "SLS": True,
        "external": {
            "disruptionType": "storm",
            "severity": 0.85
        }
    }

    dto = ReconfigurationEvent(**payload)

    assert dto.order_id == 9999
    assert dto.sls is True
    assert dto.external is not None
    assert dto.external.disruption_type == "storm"
    assert dto.external.severity == 0.85
    assert dto.delay is None

def test_reconfiguration_event_with_delay_only():
    payload = {
        "orderId": 7777,
        "SLS": False,
        "delay": {
            "dispatch_lower": 0.5,
            "dispatch_upper": 1.0,
            "shipment_lower": 1.2,
            "shipment_upper": 3.8,
            "expected_order_delivery_time": "2023-10-01T12:00:00Z",
            "estimated_order_delivery_time": "2023-10-01T16:00:00Z"
        }
    }

    dto = ReconfigurationEvent(**payload)

    assert dto.order_id == 7777
    assert dto.sls is False
    assert dto.external is None
    assert dto.delay is not None
    assert dto.delay.dispatch_lower == 0.5
    assert dto.delay.dispatch_upper == 1.0
    assert dto.delay.shipment_lower == 1.2
    assert dto.delay.shipment_upper == 3.8
    assert dto.delay.total_lower == 1.7
    assert dto.delay.total_upper == 4.8

def test_reconfiguration_event_minimal_payload():
    payload = {
        "orderId": 5678,
        "SLS": True
    }

    dto = ReconfigurationEvent(**payload)

    assert dto.order_id == 5678
    assert dto.sls is True
    assert dto.external is None
    assert dto.delay is None

def test_reconfiguration_event_invalid_missing_fields():
    payload = {
        "SLS": True
        # Missing orderId
    }

    with pytest.raises(ValidationError) as exc_info:
        ReconfigurationEvent(**payload)             # type: ignore

    assert "orderId" in str(exc_info.value)
