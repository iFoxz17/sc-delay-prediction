import pytest
import datetime
from unittest.mock import patch
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.api_gateway import APIGatewayRestResolver

from model_route.order_route import register_routes, ORDERS_BASE_PATH
from model_service.exception.order_not_found_exception import OrderNotFoundException

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

def test_handle_get_orders_success(app):
    with patch("model_route.order_route.get_orders", return_value=[]):
        event = make_event(ORDERS_BASE_PATH)
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 200
        # Optionally check response body content
        body = response.get("body")
        assert body is not None

def test_handle_get_orders_internal_error(app):
    with patch("model_route.order_route.get_orders", side_effect=Exception("Test Exception")):
        event = make_event(ORDERS_BASE_PATH)
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 500

def test_handle_get_order_by_id_success(app):
    with patch("model_route.order_route.get_order_by_id", return_value={"id": 123}):
        event = make_event(f"{ORDERS_BASE_PATH}/123")
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 200
        # Check response body contains the mocked order id
        body = response.get("body")
        assert '"id": 123' in body

def test_handle_get_order_by_id_bad_request(app):
    event = make_event(f"{ORDERS_BASE_PATH}/abc")
    response = app.resolve(event, LambdaContext())
    assert response["statusCode"] == 400

def test_handle_get_order_by_id_not_found(app):
    with patch("model_route.order_route.get_order_by_id", side_effect=OrderNotFoundException("Order not found")):
        event = make_event(f"{ORDERS_BASE_PATH}/123")
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 404

def test_handle_get_order_by_id_internal_error(app):
    with patch("model_route.order_route.get_order_by_id", side_effect=Exception("Test Exception")):
        event = make_event(f"{ORDERS_BASE_PATH}/123")
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 500


from model_dto.order_patch_dto import OrderPatchDTO

def test_handle_patch_order_success(app):
    patch_data = OrderPatchDTO(
        manufacturer_estimated_delivery=datetime.datetime.fromisoformat("2025-08-01T10:00:00"),
        manufacturer_confirmed_delivery=None,
        srs=True
    )

    with patch("model_route.order_route.patch_order_by_id", return_value={"id": 1, "status": "UPDATED"}) as mock_patch:
        event = {
            "httpMethod": "PATCH",
            "path": f"{ORDERS_BASE_PATH}/1",
            "queryStringParameters": {},
            "body": patch_data.model_dump_json(),  # pydantic v2
            "headers": {
                "Content-Type": "application/json"
            },
            "isBase64Encoded": False
        }

        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 200
        assert '"status": "UPDATED"' in response["body"]

        mock_patch.assert_called_once()
        args = mock_patch.call_args[0]
        assert args[0] == 1  # order_id
        assert args[1].name == "ID"  # By.ID

def test_handle_patch_order_not_found(app):
    patch_data = OrderPatchDTO(
        manufacturer_estimated_delivery= datetime.datetime.fromisoformat("2025-08-01T10:00:00"),
    )

    with patch("model_route.order_route.patch_order_by_id", side_effect=OrderNotFoundException("Order not found")):
        event = {
            "httpMethod": "PATCH",
            "path": f"{ORDERS_BASE_PATH}/999",
            "queryStringParameters": {},
            "body": patch_data.model_dump_json(),
            "headers": {
                "Content-Type": "application/json"
            },
            "isBase64Encoded": False
        }

        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 404
        assert "Order not found" in response["body"]

def test_handle_patch_order_invalid_id(app):
    event = {
        "httpMethod": "PATCH",
        "path": f"{ORDERS_BASE_PATH}/invalid",
        "queryStringParameters": {},
        "body": '{}',
        "headers": {
            "Content-Type": "application/json"
        },
        "isBase64Encoded": False
    }

    response = app.resolve(event, LambdaContext())

    assert response["statusCode"] == 400
    assert "Invalid order ID format" in response["body"]

