from typing import Dict, Any, List, TYPE_CHECKING

from utils.parsing import get_query_params
from utils.response import internal_error_response, not_found_response, success_response, bad_request_response
from logger import get_logger

from resolver.vertex_not_found_exception import VertexNotFoundException

from model_dto.q_params import VerticesQParamsKeys
from model_service.vertex_service import get_vertex_by_id, get_vertices

if TYPE_CHECKING:
    from aws_lambda_powertools.event_handler import APIGatewayRestResolver
    from aws_lambda_powertools.event_handler.api_gateway import Response

logger = get_logger(__name__)
VERTEX_BASE_PATH = "/vertices"

def register_routes(app: 'APIGatewayRestResolver') -> None:
    @app.get(VERTEX_BASE_PATH)
    def handle_get_vertices() -> 'Response':
        q_params: Dict[str, str] = get_query_params(
            app.current_event.query_string_parameters,
            allowed_keys=VerticesQParamsKeys.get_all_keys()
        )
        logger.debug(f"Filtered query parameters for /vertices: {q_params}")
        
        vertices_data: List[Dict[str, Any]] = get_vertices(q_params)
        return success_response(data=vertices_data)
    
    @app.get(f"{VERTEX_BASE_PATH}/<id>")
    def handle_get_vertex_by_id(id: str) -> 'Response':
        try:
            vertex_id: int = int(id)
        except ValueError:
            logger.info(f"Invalid vertex ID format: {id}")
            return bad_request_response(f"Invalid vertex ID format: {id}")
        
        vertex_data: Dict[str, Any] = get_vertex_by_id(vertex_id)
        return success_response(data=vertex_data)
        
    @app.exception_handler(Exception)
    def handle_exception(ex: Exception) -> 'Response':
        if isinstance(ex, VertexNotFoundException):
            logger.warning(f"Vertex not found: {str(ex)}")
            return not_found_response(str(ex))

        logger.error(f"Unexpected error occurred: {str(ex)}", exc_info=True)
        return internal_error_response(f"Unexpected error occurred: {str(ex)}")
