import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from utils.parsing import parse_as
from api.dto.order_estimation.order_estimation_request import OrderEstimationRequestDTO, OrderEstimationRequestListDTO, OrderEstimationRequest
from model.vertex import VertexType

def make_order_payload(order_id=1, event_time=None, vertex=None):
    if event_time is None:
        event_time = datetime(2025, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
    payload = {
        "orderId": order_id,
        "eventTime": event_time.isoformat(),
    }
    if vertex is not None:
        payload["vertex"] = vertex
    return payload

def test_single_order_estimation_request():
    payload = make_order_payload(vertex={"vertexName": "vertex1", "vertexType": "MANUFACTURER"})
    dto: OrderEstimationRequestDTO = parse_as(OrderEstimationRequestDTO, payload)
    assert dto.order_id == payload["orderId"]
    assert dto.vertex is not None
    assert dto.vertex.vertex_name == "vertex1"
    assert dto.vertex.vertex_type == VertexType.MANUFACTURER
    assert isinstance(dto.event_time, datetime)
    assert isinstance(dto.estimation_time, datetime)

def test_order_estimation_request_list():
    payload_list = [
        make_order_payload(order_id=1, vertex={"vertexName": "vertex1"}),
        make_order_payload(order_id=2, vertex={"vertexName": "vertex2", "vertexType": "SUPPLIER_SITE"}),
    ]
    dto_list: OrderEstimationRequestListDTO = parse_as(OrderEstimationRequestListDTO, payload_list)
    assert len(dto_list.root) == 2
    assert dto_list.root[0].order_id == 1
    assert dto_list.root[1].vertex.vertex_name == "vertex2"
    assert dto_list.root[1].vertex.vertex_type == VertexType.SUPPLIER_SITE

def test_order_estimation_request_list_empty_raises():
    with pytest.raises(ValidationError):
        OrderEstimationRequestListDTO.model_validate([])

def test_union_parsing():
    single_payload = make_order_payload(order_id=10, vertex={"vertexName": "single"})
    list_payload = [
        make_order_payload(order_id=11, vertex={"vertexName": "list1", "vertex_type": "INTERMEDIATE"}),
        make_order_payload(order_id=12, vertex={"vertexName": "list2"}),
    ]

    single_dto = parse_as(OrderEstimationRequestDTO, single_payload)
    assert isinstance(single_dto, OrderEstimationRequestDTO)

    list_dto = parse_as(OrderEstimationRequestListDTO, list_payload)
    assert isinstance(list_dto, OrderEstimationRequestListDTO)
    assert len(list_dto.root) == 2
    assert list_dto.root[0].vertex.vertex_type == VertexType.INTERMEDIATE
