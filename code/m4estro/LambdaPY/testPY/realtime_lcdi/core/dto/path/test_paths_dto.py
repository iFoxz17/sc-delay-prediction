import pytest
from pydantic import ValidationError

from core.dto.path.paths_dto import PathsIdDTO, PathsNameDTO
from core.dto.path.prob_path_dto import ProbPathIdDTO, ProbPathNameDTO


@pytest.mark.parametrize("dto_cls,prob_dto_cls,source,destination,paths", [
    (
        PathsIdDTO, ProbPathIdDTO,
        1, 6,
        [
            ProbPathIdDTO(path=[1, 2, 6], prob=0.2, carrier="dhl"),
            ProbPathIdDTO(path=[1, 2, 5, 6], prob=0.3, carrier="dhl"),
            ProbPathIdDTO(path=[1, 3, 4, 6], prob=0.3, carrier="ups"),
            ProbPathIdDTO(path=[1, 3, 4, 5, 6], prob=0.2, carrier="ups"),
        ]
    ),
    (
        PathsNameDTO, ProbPathNameDTO,
        "A", "F",
        [
            ProbPathNameDTO(path=["A", "B", "F"], prob=0.25, carrier="dhl"),
            ProbPathNameDTO(path=["A", "B", "E", "F"], prob=0.35, carrier="dhl"),
            ProbPathNameDTO(path=["A", "C", "D", "F"], prob=0.25, carrier="ups"),
            ProbPathNameDTO(path=["A", "C", "D", "E", "F"], prob=0.15, carrier="ups"),
        ]
    ),
])
def test_valid_paths_dto(dto_cls, prob_dto_cls, source, destination, paths):
    dto = dto_cls(
        source=source,
        destination=destination,
        requestedCarriers=["dhl", "ups"],
        validCarriers=["dhl", "ups"],
        paths=paths
    )
    assert dto.source == source
    assert dto.destination == destination
    assert dto.n_paths == 4
    assert abs(dto.total_probability - 1.0) < 1e-6


@pytest.mark.parametrize("dto_cls,prob_dto_cls,source,destination,paths", [
    (
        PathsIdDTO, ProbPathIdDTO,
        0, 2,
        [
            ProbPathIdDTO(path=[0, 1, 2], prob=0.6, carrier="dhl"),
            ProbPathIdDTO(path=[0, 2], prob=0.5, carrier="dhl"),
        ]
    ),
    (
        PathsNameDTO, ProbPathNameDTO,
        "S", "T",
        [
            ProbPathNameDTO(path=["S", "X", "T"], prob=0.7, carrier="ups"),
            ProbPathNameDTO(path=["S", "T"], prob=0.4, carrier="ups"),
        ]
    ),
])
def test_probability_sum_error(dto_cls, prob_dto_cls, source, destination, paths):
    with pytest.raises(ValidationError) as exc_info:
        dto_cls(
            source=source,
            destination=destination,
            requestedCarriers=["dhl", "ups"],
            validCarriers=["dhl", "ups"],
            paths=paths
        )
    assert "Sum of" in str(exc_info.value)


@pytest.mark.parametrize("dto_cls,prob_dto_cls,source,destination,paths", [
    (
        PathsIdDTO, ProbPathIdDTO,
        0, 1,
        [ProbPathIdDTO(path=[0, 1], prob=1.0, carrier="dhl")]
    ),
    (
        PathsNameDTO, ProbPathNameDTO,
        "A", "B",
        [ProbPathNameDTO(path=["A", "B"], prob=1.0, carrier="dhl")]
    ),
])
def test_extra_fields_forbidden(dto_cls, prob_dto_cls, source, destination, paths):
    with pytest.raises(ValidationError):
        dto_cls(
            source=source,
            destination=destination,
            carriers=["dhl"],
            paths=paths,
            extra_field="forbidden"  # type: ignore
        )


@pytest.mark.parametrize("dto_cls,prob_dto_cls,source,destination,paths", [
    (
        PathsIdDTO, ProbPathIdDTO,
        0, 1,
        [ProbPathIdDTO(path=[0, 1], prob=1.0, carrier="dhl")]
    ),
    (
        PathsNameDTO, ProbPathNameDTO,
        "A", "B",
        [ProbPathNameDTO(path=["A", "B"], prob=1.0, carrier="dhl")]
    ),
])
def test_validate_assignment_prob_change(dto_cls, prob_dto_cls, source, destination, paths):
    dto = dto_cls(
        source=source,
        destination=destination,
        requestedCarriers=["dhl"],
        validCarriers=["dhl"],
        paths=paths
    )
    with pytest.raises(ValidationError):
        dto.paths[0].prob = 1.5  # violates upper bound
