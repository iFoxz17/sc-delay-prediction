import pytest
from pydantic import ValidationError

from utils.parsing import parse_as

from api.dto.order_estimation.order_estimation_response import (
    OrderEstimationStatus,
    OrderEstimationCreatedDTO,
    OrderEstimationFailedDTO,
    OrderEstimationResponse,
)

def test_created_dto_valid():
    payload = {
        "status": "CREATED",
        "id": 42,
        "location": "/lcdi/realtime/42",
    }
    dto = OrderEstimationCreatedDTO.model_validate(payload)
    assert dto.status == OrderEstimationStatus.CREATED
    assert dto.id == 42
    assert dto.location == "/lcdi/realtime/42"

def test_failed_dto_valid():
    payload = {
        "status": "FAILED",
        "message": "Computation error.",
    }
    dto = OrderEstimationFailedDTO.model_validate(payload)
    assert dto.status == OrderEstimationStatus.FAILED
    assert dto.message == "Computation error."

def test_created_dto_missing_fields_raises():
    payload = {
        "status": "CREATED",
        "location": "/missing/id"
    }
    with pytest.raises(ValidationError):
        OrderEstimationCreatedDTO.model_validate(payload)

def test_failed_dto_missing_message_raises():
    payload = {
        "status": "FAILED"
    }
    with pytest.raises(ValidationError):
        OrderEstimationFailedDTO.model_validate(payload)

def test_union_single_created():
    payload = {
        "status": "CREATED",
        "id": 1,
        "location": "/lcdi/realtime/1"
    }
    dto = OrderEstimationCreatedDTO.model_validate(payload)
    assert isinstance(dto, OrderEstimationCreatedDTO)

def test_union_single_failed():
    payload = {
        "status": "FAILED",
        "message": "Error occurred"
    }
    dto = OrderEstimationFailedDTO.model_validate(payload)
    assert isinstance(dto, OrderEstimationFailedDTO)

def test_union_list_parsing():
    payloads = [
        {"status": "CREATED", "id": 1, "location": "/lcdi/realtime/1"},
        {"status": "FAILED", "message": "Internal error"},
    ]
    dtos: OrderEstimationResponse = parse_as(OrderEstimationResponse, payloads)
    assert isinstance(dtos[0], OrderEstimationCreatedDTO)
    assert isinstance(dtos[1], OrderEstimationFailedDTO)

def test_invalid_status_raises():
    payload = {
        "status": "UNKNOWN",
        "id": 1,
        "location": "/some/path"
    }
    with pytest.raises(ValidationError):
        OrderEstimationCreatedDTO.model_validate(payload)
