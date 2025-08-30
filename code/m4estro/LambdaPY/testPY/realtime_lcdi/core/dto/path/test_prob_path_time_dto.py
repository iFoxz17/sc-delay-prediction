import pytest
from pydantic import ValidationError
from core.dto.path.prob_path_time_dto import ProbPathIdTimeDTO, ProbPathNameTimeDTO


@pytest.mark.parametrize("dto_cls,path", [
    (ProbPathIdTimeDTO, [1, 2, 3]),
    (ProbPathNameTimeDTO, ["a", "b", "c"]),
])
@pytest.mark.parametrize("lower_time", [-1, -0.1, "invalid"])
def test_invalid_lower_time(dto_cls, path, lower_time):
    with pytest.raises(ValidationError):
        dto_cls(
            path=path,
            prob=0.5,
            lower_time=lower_time,
            upper_time=13.0,
            avg_tmi=0.2,
            avg_wmi=0.3,
            carrier="FedEx"
        )


@pytest.mark.parametrize("dto_cls,path", [
    (ProbPathIdTimeDTO, [1, 2, 3]),
    (ProbPathNameTimeDTO, ["a", "b", "c"]),
])
@pytest.mark.parametrize("upper_time", [-1, -0.1, "invalid"])
def test_invalid_upper_time(dto_cls, path, upper_time):
    with pytest.raises(ValidationError):
        dto_cls(
            path=path,
            prob=0.5,
            lower_time=10.0,
            upper_time=upper_time,
            avg_tmi=0.2,
            avg_wmi=0.3,
            carrier="FedEx"
        )


@pytest.mark.parametrize("dto_cls,path", [
    (ProbPathIdTimeDTO, [1, 2, 3]),
    (ProbPathNameTimeDTO, ["a", "b", "c"]),
])
@pytest.mark.parametrize("lower_time, upper_time", [
    (15.0, 10.0),
    (13.2, 11.2),
])
def test_lower_time_not_greater_than_upper_time(dto_cls, path, lower_time, upper_time):
    with pytest.raises(ValidationError):
        dto_cls(
            path=path,
            prob=0.5,
            lower_time=lower_time,
            upper_time=upper_time,
            avg_tmi=0.2,
            avg_wmi=0.3,
            carrier="FedEx"
        )


@pytest.mark.parametrize("dto_cls,path", [
    (ProbPathIdTimeDTO, [1, 2, 3]),
    (ProbPathNameTimeDTO, ["a", "b", "c"]),
])
@pytest.mark.parametrize("avg_tmi", [-0.1, 1.1, "bad"])
def test_invalid_avg_tmi(dto_cls, path, avg_tmi):
    with pytest.raises(ValidationError):
        dto_cls(
            path=path,
            prob=0.5,
            lower_time=5.0,
            upper_time=10.0,
            avg_tmi=avg_tmi,
            avg_wmi=0.3,
            carrier="FedEx"
        )


@pytest.mark.parametrize("dto_cls,path", [
    (ProbPathIdTimeDTO, [1, 2, 3]),
    (ProbPathNameTimeDTO, ["a", "b", "c"]),
])
@pytest.mark.parametrize("avg_wmi", [-0.2, 1.5, "bad"])
def test_invalid_avg_wmi(dto_cls, path, avg_wmi):
    with pytest.raises(ValidationError):
        dto_cls(
            path=path,
            prob=0.5,
            lower_time=5.0,
            upper_time=10.0,
            avg_tmi=0.2,
            avg_wmi=avg_wmi,
            carrier="FedEx"
        )


@pytest.mark.parametrize("dto_cls,path", [
    (ProbPathIdTimeDTO, [1, 2, 3]),
    (ProbPathNameTimeDTO, ["a", "b", "c"]),
])
def test_valid_prob_path_time_dto(dto_cls, path):
    dto = dto_cls(
        path=path,
        prob=0.6,
        lower_time=8.0,
        upper_time=12.0,
        avg_tmi=0.4,
        avg_wmi=0.5,
        carrier="FedEx"
    )
    assert dto.lower_time == 8.0
    assert dto.upper_time == 12.0
    assert dto.avg_tmi == 0.4
    assert dto.avg_wmi == 0.5
    assert dto.path == path
    assert dto.prob == 0.6
    assert dto.carrier == "FedEx"
