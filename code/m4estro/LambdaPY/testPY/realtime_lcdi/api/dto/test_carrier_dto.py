import pytest
from pydantic import ValidationError

from utils.parsing import parse_as

from api.dto.carrier_dto import CarrierIdDTO, CarrierNameDTO, CarrierDTO

def test_single_carrier_id_dto():
    payload = {"carrierId": 123}
    dto = CarrierIdDTO(**payload)
    assert dto.carrier_id == 123

def test_single_carrier_name_dto():
    payload = {"carrierName": "FastCarrier"}
    dto = CarrierNameDTO(**payload)
    assert dto.carrier_name == "FastCarrier"

def test_carrier_data_dto_union_accepts_id_and_name():
    id_payload = {"carrierId": 101}
    name_payload = {"carrierName": "Speedy"}

    dto_id = parse_as(CarrierDTO, id_payload)           # type: ignore
    dto_name = parse_as(CarrierDTO, name_payload)       # type: ignore

    assert isinstance(dto_id, CarrierIdDTO)
    assert dto_id.carrier_id == 101

    assert isinstance(dto_name, CarrierNameDTO)
    assert dto_name.carrier_name == "Speedy"

def test_carrier_dto_union_accepts_single_and_list():
    # Single CarrierIdDTO
    single_id_payload = {"carrierId": 10, "extra": ""}
    carrier_dto = parse_as(CarrierDTO, single_id_payload)       # type: ignore
    assert isinstance(carrier_dto, CarrierIdDTO)
    assert carrier_dto.carrier_id == 10

    # Single CarrierNameDTO
    single_name_payload = {"carrierName": "Alpha", "extra": ""}
    carrier_dto = parse_as(CarrierDTO, single_name_payload)     # type: ignore
    assert isinstance(carrier_dto, CarrierNameDTO)
    assert carrier_dto.carrier_name == "Alpha"

def test_invalid_carrier_dto_raises():
    invalid_payload = {"unknownField": 123}
    with pytest.raises(ValidationError):
        carrier_dto = parse_as(CarrierDTO, invalid_payload)     # type: ignore
