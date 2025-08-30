from typing import Dict, List, Any, TYPE_CHECKING
from pydantic import ValidationError

from utils.parsing import get_query_params, parse_as, get_query_params
from utils.response import internal_error_response, not_found_response, success_response, bad_request_response
from logger import get_logger

from model_dto.q_params import OrdersQParamsKeys, By
from model_dto.order_patch_dto import OrderPatchDTO

from model_service.order_service import get_orders, get_order_by_id, patch_order_by_id
from model_service.exception.order_not_found_exception import OrderNotFoundException

if TYPE_CHECKING:
    from aws_lambda_powertools.event_handler import APIGatewayRestResolver
    from aws_lambda_powertools.event_handler.api_gateway import Response

logger = get_logger(__name__)
ORDERS_BASE_PATH = "/orders"

def register_routes(app: 'APIGatewayRestResolver') -> None:
    @app.get(ORDERS_BASE_PATH)
    def handle_get_orders() -> 'Response':
        q_params: Dict[str, str] = get_query_params(
            app.current_event.query_string_parameters,
            allowed_keys={OrdersQParamsKeys.STATUS.value}
        )
        logger.debug(f"Filtered query parameters for /orders: {q_params}")
        
        orders_data: List[Dict[str, Any]] = get_orders(q_params)
        return success_response(orders_data)

    @app.get(f"{ORDERS_BASE_PATH}/<id>")    
    def handle_get_order_by_id(id: str) -> 'Response':
        try:
            order_id: int = int(id)
        except ValueError:
            logger.info(f"Invalid order ID format: {id}")
            return bad_request_response(f"Invalid order ID format: {id}")
        
        order_data: Dict[str, Any] = get_order_by_id(order_id)
        return success_response(order_data)
    
    @app.patch(f"{ORDERS_BASE_PATH}/<id>")
    def handle_patch_order(id: str) -> 'Response':
        try:
            order_id: int = int(id)
        except ValueError:
            logger.info(f"Invalid order ID format: {id}")
            return bad_request_response(f"Invalid order ID format: {id}")
        
        q_params: Dict[str, str] = get_query_params(
            app.current_event.query_string_parameters,
            allowed_keys={OrdersQParamsKeys.BY.value}
        )
        by_str: str = q_params.get(OrdersQParamsKeys.BY.value, By.ID.value)
        try:
            by: By = By[by_str.upper()]
        except KeyError:
            logger.info(f"Invalid 'by' parameter: {by_str}. Defaulting to ID.")
            by = By.ID

        payload: Dict[str, Any] = app.current_event.json_body
        try:
            payload_parsed: OrderPatchDTO = parse_as(OrderPatchDTO, payload)
        except ValidationError as e:
            logger.info(f"Invalid payload for patching order: {e}")
            return bad_request_response(f"Invalid payload: {e}")

        logger.info(f"Update order request received for ID: {id}")
        order_data: Dict[str, Any] = patch_order_by_id(order_id,
                                                       by,
                                                       payload_parsed)

        return success_response(order_data)

    @app.exception_handler(Exception)
    def handle_exception(ex: Exception) -> 'Response':
        if isinstance(ex, OrderNotFoundException):
            logger.warning(f"Order not found: {str(ex)}")
            return not_found_response(str(ex))

        logger.error(f"Unexpected error occurred: {str(ex)}", exc_info=True)
        return internal_error_response(f"Unexpected error occurred: {str(ex)}")