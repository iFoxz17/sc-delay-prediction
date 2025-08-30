import pytest
from pydantic import ValidationError
from model.vertex import VertexType
from resolver.vertex_dto import VertexIdDTO, VertexNameDTO, VertexDTO

from utils.parsing import parse_as


def test_vertex_id_dto_valid():
    data = {"vertexId": 42}
    dto = VertexIdDTO(**data)
    assert dto.vertex_id == 42

def test_vertex_id_dto_missing():
    data = {}
    with pytest.raises(ValidationError):
        VertexIdDTO(**data)

def test_vertex_name_dto_valid_with_type():
    data = {"vertexName": "Factory X", "vertexType": "SUPPLIER_SITE"}
    dto = VertexNameDTO(**data)             # type: ignore
    assert dto.vertex_name == "Factory X"
    assert dto.vertex_type == VertexType.SUPPLIER_SITE

def test_vertex_name_dto_valid_with_mispelled_type():
    data = {"vertexName": "Factory X", "vertexType": "SupplierSite"}
    dto = VertexNameDTO(**data)         # type: ignore
    assert dto.vertex_name == "Factory X"
    assert dto.vertex_type == VertexType.SUPPLIER_SITE

    
    data = {"vertexName": "Factory X", "vertexType": "supPlier"}
    dto = VertexNameDTO(**data)         # type: ignore
    assert dto.vertex_name == "Factory X"
    assert dto.vertex_type == VertexType.SUPPLIER_SITE

    data = {"vertexName": "Factory X", "vertexType": "Site"}
    dto = VertexNameDTO(**data)         # type: ignore
    assert dto.vertex_name == "Factory X"
    assert dto.vertex_type == VertexType.SUPPLIER_SITE

def test_vertex_name_dto_valid_without_type():
    data = {"vertexName": "Factory X"}
    dto = VertexNameDTO(**data)         # type: ignore
    assert dto.vertex_name == "Factory X"
    assert dto.vertex_type is None

def test_vertex_name_dto_invalid_type():
    data = {"vertexName": "Factory X", "vertexType": "UNKNOWN_TYPE"}
    with pytest.raises(ValidationError):
        VertexNameDTO(**data)           # type: ignore

def test_union_vertexdto_with_vertex_id():
    data = {"vertexId": 123}
    dto: VertexIdDTO = parse_as(VertexIdDTO, data)
    assert isinstance(dto, VertexIdDTO)
    assert dto.vertex_id == 123

def test_union_vertexdto_with_vertex_name_camel_case():
    data = {"vertexName": "Test", "vertexType": "INTeRMEDiATE", "ignored": "ignored_value"}
    dto: VertexNameDTO = parse_as(VertexNameDTO, data)
    assert isinstance(dto, VertexNameDTO)
    assert dto.vertex_name == "Test"
    assert dto.vertex_type == VertexType.INTERMEDIATE

def test_union_vertexdto_with_vertex_name_snake_case():
    data = {"vertex_name": "Test", "vertex_type": "manUFACTURER", "ignored": "ignored_value"}
    dto: VertexNameDTO = parse_as(VertexNameDTO, data)
    assert isinstance(dto, VertexNameDTO)
    assert dto.vertex_name == "Test"
    assert dto.vertex_type == VertexType.MANUFACTURER

def test_union_vertexdto_invalid():
    data = {"unknownField": 999}
    with pytest.raises(ValidationError):
        # None of the DTOs should accept this
        for DTO in (VertexIdDTO, VertexNameDTO):
            DTO(**data)                             # type: ignore      

