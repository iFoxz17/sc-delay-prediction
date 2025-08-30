from typing import Dict, List, Any, TYPE_CHECKING

from utils.response import (
    success_response, internal_error_response, bad_request_response
)
from utils.parsing import get_query_params

from api.dto.qparam import PathQParamKeys
from api.exception.bad_vertex_ids_exception import BadVertexIdsException
from api.exception.bad_carrier_names_exception import BadCarrierNamesException
from api.service.path_service import get_prob_paths

from core.dto.path.paths_dto import PathsIdDTO, PathsNameDTO

from logger import get_logger

if TYPE_CHECKING:
    from aws_lambda_powertools.event_handler import APIGatewayRestResolver
    from aws_lambda_powertools.event_handler.api_gateway import Response

logger = get_logger(__name__)
from graph_config import SC_GRAPH_PATH

def register_routes(app: 'APIGatewayRestResolver') -> None:
    @app.get(f"{SC_GRAPH_PATH}/paths")
    def handle_retrieve_paths() -> 'Response':
        q_params: Dict[str, str] = get_query_params(
            app.current_event.query_string_parameters,
            allowed_keys=PathQParamKeys.get_all_values()
        )

        try:
            paths: List[PathsIdDTO | PathsNameDTO] = get_prob_paths(q_params)
        except (BadVertexIdsException, BadCarrierNamesException) as e:
            return bad_request_response(str(e))
        
        paths_data: List[Dict[str, Any]] = [p.model_dump(by_alias=True) for p in paths]
        return success_response(data=paths_data)

    @app.exception_handler(Exception)
    def handle_exception(ex: Exception) -> 'Response':
        logger.error(f"Unexpected error occurred: {str(ex)}", exc_info=True)
        return internal_error_response(f"Unexpected error occurred: {str(ex)}")