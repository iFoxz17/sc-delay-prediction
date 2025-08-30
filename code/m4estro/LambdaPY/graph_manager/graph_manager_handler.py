from typing import Dict, Any
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.api_gateway import Response

from builder_service.exception.s3_bucket_object_deletion_exception import S3BucketObjectDeletionException
from builder_service.graph_builder_service import build_graph
from exporter_service.graph_exporter_service import get_graph_data, get_map_data

from utils.parsing import get_query_params
from utils.response import internal_error_response, created_response, success_response

from graph_manager_dto.q_params import GraphManagerQParamsKeys

from logger import get_logger
logger = get_logger(__name__)

from graph_config import SC_GRAPH_PATH

app = APIGatewayRestResolver()

@app.get(SC_GRAPH_PATH)
def handle_graph_retrieval() -> Response:
    intermediate_q_param_key = GraphManagerQParamsKeys.INTERMEDIATE.value
    q_params: Dict[str, str] = get_query_params(app.current_event.query_string_parameters, allowed_keys={intermediate_q_param_key})
    logger.debug(f"Filtered query parameters for /orders: {q_params}")

    exclude_intermediates: bool = q_params.get(intermediate_q_param_key, "").lower() == "false"
    logger.debug(f"Exclude intermediates: {exclude_intermediates}")

    data: Dict[str, Any] = get_map_data() if exclude_intermediates else get_graph_data()
    logger.debug(f"Data retrieved successfully, exclude intermediates: {exclude_intermediates}")
    return success_response(data)


@app.post(SC_GRAPH_PATH)
def handle_graph_build() -> Response:
    try:
        build_graph()
    except S3BucketObjectDeletionException as e:
        logger.error(f"Error deleting S3 bucket object: {e}")
        return internal_error_response(f"Error deleting S3 bucket object: {str(e)}")

    logger.debug("Graph build completed successfully")
    return created_response(location_url=SC_GRAPH_PATH)
    
    
@app.exception_handler(Exception)
def handle_exception(ex: Exception) -> 'Response':
    logger.error(f"Unexpected error occurred: {str(ex)}", exc_info=True)
    return internal_error_response(f"Unexpected error occurred: {str(ex)}")


def handler(event: Dict, context: LambdaContext) -> Dict:
    return app.resolve(event, context)