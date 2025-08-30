import pytest
from datetime import datetime, timezone

from utils.parsing import parse_as

from model.vertex import VertexType

from api.dto.vertex_estimation.vertex_estimation_request import (
    VertexEstimationRequestDTO,
    VertexEstimationRequestListDTO,
    VertexEstimationRequest
)

def make_payload(**overrides):
    base = {
        "vertex": {
            "vertexName": "vertex1",
            "vertexType": "intermediate"
        },
        "carrier": {"carrierName": "carrier1"},
        "site": {
            "siteId": 12345
        },
        "orderTime": "2025-06-27T10:00:00Z",
        "eventTime": "2025-06-27T10:30:00Z",
        "estimationTime": "2025-06-27T11:00:00Z",
        # "shipmentTime": ...
        
    }
    base.update(overrides)
    return base

def test_vertex_estimation_request_dto_minimal():
    payload = make_payload()
    dto = VertexEstimationRequestDTO(**payload)

    assert dto.vertex.vertex_name == "vertex1"                      # type: ignore  
    assert dto.vertex.vertex_type == VertexType.INTERMEDIATE        # type: ignore
    assert dto.carrier.carrier_name == "carrier1"                   # type: ignore
    assert dto.site.site_id == 12345
    assert dto.order_time == datetime(2025, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
    assert dto.event_time == datetime(2025, 6, 27, 10, 30, 0, tzinfo=timezone.utc)
    assert dto.estimation_time == datetime(2025, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
    assert dto.maybe_shipment_time is None


def test_vertex_estimation_request_list_dto_accepts_non_empty():
    payloads = [
        {
            "vertex": {"vertexName": "v1", "vertexType": "intermediate"},
            "carrier": {"carrierName": "c1"},
            "site": {"siteId": 111},
            "orderTime": "2025-06-27T09:00:00Z",
            "eventTime": "2025-06-27T09:15:00Z",
            "estimationTime": "2025-06-27T09:30:00Z"
        },
        {
            "vertex": {"vertexName": "v2", "vertexType": "intermediate"},
            "carrier": {"carrierName": "c2"},
            "site": {"siteId": 222},
            "orderTime": "2025-06-27T10:00:00Z",
            "eventTime": "2025-06-27T10:15:00Z",
            "estimationTime": "2025-06-27T10:30:00Z"
        }
    ]

    dto_list = VertexEstimationRequestListDTO(payloads)                 # type: ignore
    assert len(dto_list.root) == 2
    assert dto_list.root[0].vertex.vertex_name == "v1"                  # type: ignore

def test_vertex_estimation_request_list_dto_rejects_empty():
    with pytest.raises(ValueError, match="Request list must not be empty."):
        VertexEstimationRequestListDTO([])

def test_union_accepts_dto_and_list():
    single_payload = make_payload()
    list_payload = [
        make_payload(),
        make_payload(vertex={"vertexName": "vertex2", "vertexType": "intermediate"})
    ]

    # Single DTO
    dto = parse_as(VertexEstimationRequestDTO, single_payload)
    assert isinstance(dto, VertexEstimationRequestDTO)

    # List DTO
    dto_list = parse_as(VertexEstimationRequestListDTO, list_payload)       # type: ignore
    assert isinstance(dto_list, VertexEstimationRequestListDTO)
    assert len(dto_list.root) == 2
