import pytest
from unittest.mock import patch
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.api_gateway import APIGatewayRestResolver

from model_route.vertex_route import register_routes, VERTEX_BASE_PATH
from resolver.vertex_not_found_exception import VertexNotFoundException

@pytest.fixture
def app():
    app = APIGatewayRestResolver()
    register_routes(app)
    return app

def make_event(path: str, method="GET", query_params=None):
    return {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query_params or {}
    }

def test_handle_get_vertices_success(app):
    with patch("model_route.vertex_route.get_vertices", return_value=[]):
        with patch("model_route.vertex_route.get_query_params", return_value={}):
            event = make_event(VERTEX_BASE_PATH)
            response = app.resolve(event, LambdaContext())
            assert response["statusCode"] == 200
            assert "[]" in response.get("body", "")

def test_handle_get_vertices_internal_error(app):
    with patch("model_route.vertex_route.get_vertices", side_effect=Exception("Unexpected")):
        with patch("model_route.vertex_route.get_query_params", return_value={}):
            event = make_event(VERTEX_BASE_PATH)
            response = app.resolve(event, LambdaContext())
            assert response["statusCode"] == 500

def test_handle_get_vertex_by_id_success(app):
    with patch("model_route.vertex_route.get_vertex_by_id", return_value={"id": 123}):
        event = make_event(f"{VERTEX_BASE_PATH}/123")
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 200
        assert '"id": 123' in response.get("body", "")

def test_handle_get_vertex_by_id_bad_request(app):
    event = make_event(f"{VERTEX_BASE_PATH}/abc")
    response = app.resolve(event, LambdaContext())
    assert response["statusCode"] == 400
    assert "Invalid vertex ID format" in response.get("body", "")

def test_handle_get_vertex_by_id_not_found(app):
    with patch("model_route.vertex_route.get_vertex_by_id", side_effect=VertexNotFoundException("Vertex not found")):
        event = make_event(f"{VERTEX_BASE_PATH}/999")
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 404
        assert "Vertex not found" in response.get("body", "")

def test_handle_get_vertex_by_id_internal_error(app):
    with patch("model_route.vertex_route.get_vertex_by_id", side_effect=Exception("Database error")):
        event = make_event(f"{VERTEX_BASE_PATH}/123")
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 500
