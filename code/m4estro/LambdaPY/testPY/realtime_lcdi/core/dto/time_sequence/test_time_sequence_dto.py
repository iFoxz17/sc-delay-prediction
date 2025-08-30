import pytest
from datetime import datetime, timedelta, timezone

from core.dto.time_sequence.time_sequence_dto import (
    TimeSequenceInputDTO,
    TimeSequenceDTO,
    EstimationStage
)
from core.exception.invalid_time_sequence_exception import InvalidTimeSequenceException

def utc_now():
    return datetime.now(timezone.utc)


def test_valid_time_sequence_input_dto():
    now = utc_now()
    dto = TimeSequenceInputDTO(
        order_time=now,
        event_time=now + timedelta(hours=1),
        estimation_time=now + timedelta(hours=2)
    )
    assert dto.order_time < dto.event_time < dto.estimation_time


def test_invalid_time_sequence_input_event_before_order():
    now = utc_now()
    with pytest.raises(InvalidTimeSequenceException) as exc:
        TimeSequenceInputDTO(
            order_time=now + timedelta(hours=2),
            event_time=now + timedelta(hours=1),
            estimation_time=now + timedelta(hours=3)
        )
    assert "Event time cannot be earlier than order time" in str(exc.value)


def test_invalid_time_sequence_input_estimation_before_event():
    now = utc_now()
    with pytest.raises(InvalidTimeSequenceException) as exc:
        TimeSequenceInputDTO(
            order_time=now,
            event_time=now + timedelta(hours=2),
            estimation_time=now + timedelta(hours=1)
        )
    assert "Estimation time cannot be earlier than event time" in str(exc.value)


def test_valid_time_sequence_dto_dispatch_stage():
    now = utc_now()
    dto = TimeSequenceDTO(
        order_time=now,
        shipment_time=now + timedelta(hours=5),
        event_time=now + timedelta(hours=1),
        estimation_time=now + timedelta(hours=4)
    )
    assert dto.get_estimation_stage() == EstimationStage.DISPATCH


def test_valid_time_sequence_dto_shipment_stage():
    now = utc_now()
    dto = TimeSequenceDTO(
        order_time=now,
        shipment_time=now + timedelta(hours=1),
        event_time=now + timedelta(hours=2),
        estimation_time=now + timedelta(hours=3)
    )
    assert dto.get_estimation_stage() == EstimationStage.SHIPMENT


def test_invalid_shipment_before_order():
    now = utc_now()
    with pytest.raises(InvalidTimeSequenceException) as exc:
        TimeSequenceDTO(
            order_time=now + timedelta(hours=1),
            shipment_time=now,
            event_time=now + timedelta(hours=2),
            estimation_time=now + timedelta(hours=3)
        )
    assert "Shipment time cannot be earlier than order time" in str(exc.value)


def test_invalid_shipment_between_event_and_estimation():
    now = utc_now()
    with pytest.raises(InvalidTimeSequenceException) as exc:
        TimeSequenceDTO(
            order_time=now,
            event_time=now + timedelta(hours=2),
            shipment_time=now + timedelta(hours=3),
            estimation_time=now + timedelta(hours=4)
        )
    assert "Shipment time cannot be earlier than event time and later than estimation time" in str(exc.value)


def test_shipment_event_and_estimation_time_properties():
    now = utc_now()
    dto = TimeSequenceDTO(
        order_time=now,
        event_time=now + timedelta(hours=2),
        estimation_time=now + timedelta(hours=3),
        shipment_time=now + timedelta(hours=5),
    )
    assert dto.shipment_event_time == dto.shipment_time
    assert dto.shipment_estimation_time == dto.shipment_time

    dto = TimeSequenceDTO(
        order_time=now,
        shipment_time=now + timedelta(hours=5),
        event_time=now + timedelta(hours=7),
        estimation_time=now + timedelta(hours=8),
    )
    assert dto.shipment_event_time == dto.event_time
    assert dto.shipment_estimation_time == dto.estimation_time
