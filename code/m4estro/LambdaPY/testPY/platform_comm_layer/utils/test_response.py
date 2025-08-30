import json
import pytest
from aws_lambda_powertools.event_handler.api_gateway import Response

from utils import response as rs
from utils.config import COMMON_API_HEADERS

# Patch COMMON_API_HEADERS globally for all tests
@pytest.fixture(autouse=True)
def patch_common_headers(monkeypatch):
    monkeypatch.setattr(rs, "COMMON_API_HEADERS", COMMON_API_HEADERS)


def test_success_response():
    data = {"message": "Success"}
    response = rs.success_response(data)

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert json.loads(response.body) == data
    assert response.headers["Content-Type"] == "application/json"


def test_created_response_with_data():
    location = "/resources/123"
    data = {"id": 123}
    response = rs.created_response(location, data)

    assert isinstance(response, Response)
    assert response.status_code == 201
    assert json.loads(response.body) == data
    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["Location"] == location


def test_created_response_without_data():
    location = "/resources/123"
    response = rs.created_response(location)

    assert isinstance(response, Response)
    assert response.status_code == 201
    assert response.body == ""
    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["Location"] == location


def test_bad_request_response():
    message = "Invalid input"
    response = rs.bad_request_response(message)

    assert isinstance(response, Response)
    assert response.status_code == 400
    assert json.loads(response.body) == {"message": message}
    assert response.headers["Content-Type"] == "application/json"


def test_not_found_response():
    message = "Resource not found"
    response = rs.not_found_response(message)

    assert isinstance(response, Response)
    assert response.status_code == 404
    assert json.loads(response.body) == {"message": message}
    assert response.headers["Content-Type"] == "application/json"


def test_internal_error_response():
    message = "Unexpected server error"
    response = rs.internal_error_response(message)

    assert isinstance(response, Response)
    assert response.status_code == 500
    assert json.loads(response.body) == {"message": message}
    assert response.headers["Content-Type"] == "application/json"
