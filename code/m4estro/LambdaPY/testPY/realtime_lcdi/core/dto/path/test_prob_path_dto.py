import pytest
from pydantic import ValidationError
from core.dto.path.prob_path_dto import ProbPathIdDTO, ProbPathNameDTO, ProbPathBaseDTO

# ---------- Abstract Base Class Enforcement ----------

def test_cannot_instantiate_abstract_base():
    with pytest.raises(TypeError):
        ProbPathBaseDTO(prob=0.5, carrier="X")  # type: ignore

# ---------- ProbPathIdDTO Tests ----------

def test_valid_prob_path_id_dto():
    dto = ProbPathIdDTO(path=[1, 2, 3], prob=0.9, carrier="DHL")
    assert dto.path == [1, 2, 3]
    assert dto.prob == 0.9
    assert dto.carrier == "DHL"

@pytest.mark.parametrize("path", [[1, 2, 3], [0], []])
def test_valid_path_id_values(path):
    dto = ProbPathIdDTO(path=path, prob=0.5, carrier="FedEx")
    assert dto.path == path

@pytest.mark.parametrize("prob", [-0.1, 1.1])
def test_invalid_probability_id(prob):
    with pytest.raises(ValidationError):
        ProbPathIdDTO(path=[1, 2, 3], prob=prob, carrier="DHL")

def test_empty_path_id_is_valid():
    dto = ProbPathIdDTO(path=[], prob=0.5, carrier="UPS")
    assert dto.path == []

def test_invalid_carrier_type_id():
    with pytest.raises(ValidationError):
        ProbPathIdDTO(path=[1, 2], prob=0.5, carrier=["invalid_type"])          # type: ignore

def test_extra_field_forbidden_id():
    with pytest.raises(ValidationError):
        ProbPathIdDTO(path=[1], prob=0.2, carrier="A", extra_field="not allowed")           # type: ignore

def test_assignment_validation_id():
    dto = ProbPathIdDTO(path=[0], prob=0.5, carrier="X")
    with pytest.raises(ValidationError):
        dto.prob = 1.5  # validate_assignment=True

# ---------- ProbPathNameDTO Tests ----------

def test_valid_prob_path_name_dto():
    dto = ProbPathNameDTO(path=["A", "B", "C"], prob=0.9, carrier="GLS")
    assert dto.path == ["A", "B", "C"]
    assert dto.prob == 0.9
    assert dto.carrier == "GLS"

@pytest.mark.parametrize("path", [["A", "B", "C"], ["OnlyOne"], []])
def test_valid_path_name_values(path):
    dto = ProbPathNameDTO(path=path, prob=0.5, carrier="TNT")
    assert dto.path == path

@pytest.mark.parametrize("prob", [-0.1, 1.1])
def test_invalid_probability_name(prob):
    with pytest.raises(ValidationError):
        ProbPathNameDTO(path=["A", "B"], prob=prob, carrier="GLS")

def test_empty_path_name_is_valid():
    dto = ProbPathNameDTO(path=[], prob=0.5, carrier="UPS")
    assert dto.path == []

def test_invalid_carrier_type_name():
    with pytest.raises(ValidationError):
        ProbPathNameDTO(path=["A", "B"], prob=0.5, carrier={"not": "a string"})             # type: ignore

def test_extra_field_forbidden_name():
    with pytest.raises(ValidationError):
        ProbPathNameDTO(path=["A"], prob=0.2, carrier="A", extra_field="not allowed")       # type: ignore

def test_assignment_validation_name():
    dto = ProbPathNameDTO(path=["Start"], prob=0.5, carrier="X")
    with pytest.raises(ValidationError):
        dto.prob = -0.1  # validate_assignment=True

# ---------- Cross-Type Validation ----------

def test_invalid_path_type_in_name_dto():
    with pytest.raises(ValidationError):
        ProbPathNameDTO(path=[1, 2, 3], prob=0.5, carrier="X")  # type: ignore

def test_invalid_path_type_in_id_dto():
    with pytest.raises(ValidationError):
        ProbPathIdDTO(path=["A", "B"], prob=0.5, carrier="X")  # type: ignore
