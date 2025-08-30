from typing import Dict, List, Any, TYPE_CHECKING
from collections import defaultdict
from pydantic import ValidationError

from utils.response import (
    success_response, created_response, multi_status_response, 
    internal_error_response, bad_request_response,
    unprocessable_entity_response
)
from utils.parsing import parse_as, get_query_params
from utils.config import EXTERNAL_API_LAMBDA_ARN_KEY, RT_ESTIMATOR_LAMBDA_ARN_KEY, get_env

from service.lambda_client.geo_service_lambda_client import GeoServiceLambdaClient

from core.calculator.tfst.pt.route_time.route_time_estimator import RouteTimeEstimator
from core.calculator.tfst.pt.route_time.rt_estimator_lambda_client import RTEstimatorLambdaClient
from core.serializer.bucket_data_loader import BucketDataLoader
from core.exception.invalid_time_sequence_exception import InvalidTimeSequenceException
from core.exception.prob_path_exception import ProbPathException
from core.service.calculator_service import compute_order_realtime_lcdi
from core.sc_graph.sc_graph import SCGraph
from core.sc_graph.sc_graph_resolver import SCGraphResolver, SCGraphVertexResult

from api.dto.qparam import RealtimeQParamKeys
from api.dto.order_estimation.order_estimation_request import OrderEstimationRequest, OrderEstimationRequestDTO
from api.dto.order_estimation.order_estimation_response import (
    OrderEstimationCreatedDTO, OrderEstimationFailedDTO, OrderEstimationErrorDTO, 
    OrderEstimationResponseDTO, OrderEstimationStatus
)
from api.dto.vertex_estimation.vertex_estimation_request import VertexEstimationRequestDTO, VertexEstimationRequest

from api.service.retrieval_service import get_realtime_lcdi_by_order
from api.service.volatile_calculator_service import compute_volatile_realtime_lcdi

from resolver.vertex_dto import VertexDTO
from resolver.vertex_not_found_exception import VertexNotFoundException

from logger import get_logger

if TYPE_CHECKING:
    from aws_lambda_powertools.event_handler import APIGatewayRestResolver
    from aws_lambda_powertools.event_handler.api_gateway import Response

logger = get_logger(__name__)
REALTIME_LCDI_PATH: str = "/lcdi/realtime"

def _retrieve_vertex_dto(order_estimation_dto: OrderEstimationRequestDTO) -> VertexDTO:
    if order_estimation_dto.vertex is None:
        raise ValueError("Vertex data is required in the order estimation request")

    return order_estimation_dto.vertex

def register_routes(app: 'APIGatewayRestResolver') -> None:
    @app.get(REALTIME_LCDI_PATH)
    def handle_retrieve_realtime_lcdi() -> 'Response':
        q_params: Dict[str, str] = get_query_params(
            app.current_event.query_string_parameters,
            allowed_keys={RealtimeQParamKeys.ORDER.value}
        )
        logger.debug(f"Filtered query parameters for GET {REALTIME_LCDI_PATH}: {q_params}")

        try:
            data: List[Dict[str, Any]] | Dict[str, Any] = get_realtime_lcdi_by_order(q_params)
            return success_response(data)
        except Exception as e:
            logger.exception("Unexpected error during realtime LCDI retrieval")
            return internal_error_response(f"Unexpected error during realtime LCDI retrieval: {str(e)}")

    @app.post(REALTIME_LCDI_PATH)
    def handle_compute_realtime_lcdi_from_order() -> 'Response':
        payload: Dict[str, Any] = app.current_event.json_body
        logger.debug(f"Received payload for POST {REALTIME_LCDI_PATH}: {payload}")

        try:
            payload_parsed: OrderEstimationRequest = parse_as(OrderEstimationRequest, payload)  # type: ignore
        except ValidationError as e:
            logger.info(f"Invalid request body for POST {REALTIME_LCDI_PATH}: {e}")
            return bad_request_response(f"Invalid request body: {str(e)}")

        logger.debug(f"Parsed payload: {payload_parsed}")

        requests: List[OrderEstimationRequestDTO] = (
            [payload_parsed] if isinstance(payload_parsed, OrderEstimationRequestDTO)
            else payload_parsed.root
        )
        is_single: bool = isinstance(payload_parsed, OrderEstimationRequestDTO)

        bd_loader: BucketDataLoader = BucketDataLoader()
        
        sc_graph: SCGraph = bd_loader.load_sc_graph()
        logger.debug(f"SCGraph retrieved successfully")

        geo_service_lambda_client: GeoServiceLambdaClient = GeoServiceLambdaClient(
            lambda_arn=get_env(EXTERNAL_API_LAMBDA_ARN_KEY)
        )
        vertex_resolver: SCGraphResolver = SCGraphResolver(lambda_client=geo_service_lambda_client, maybe_sc_graph=sc_graph)
        logger.debug("Vertex resolver initialized")

        results: List[OrderEstimationResponseDTO] = []

        for req in requests:
            logger.debug(f"Processing request: {req}")
            try:
                v_dto: VertexDTO = _retrieve_vertex_dto(req)
                v_result: SCGraphVertexResult = vertex_resolver.resolve(v_dto)
                resource = compute_order_realtime_lcdi(
                    vertex=v_result.vertex,
                    order_id=req.order_id,
                    event_time=req.event_time,
                    maybe_estimation_time=req.estimation_time,
                    maybe_sc_graph=sc_graph,
                    use_order_status=False
                )
                results.append(OrderEstimationCreatedDTO(
                    id=resource['id'],
                    location=f"{REALTIME_LCDI_PATH}/{resource['id']}",
                    data=resource
                ))
            except VertexNotFoundException as ex:
                logger.warning(f"Vertex not found for request {req}: {ex}")
                results.append(OrderEstimationFailedDTO(message=f"Vertex not found for request {req}: {ex}"))
            except InvalidTimeSequenceException as ex:
                logger.warning(f"Invalid time sequence for request {req}: {ex}")
                results.append(OrderEstimationFailedDTO(message=f"Invalid time sequence for request {req}: {ex}"))
            except ProbPathException as ex:
                logger.warning(f"Paths extraction failed for request {req}: {ex}")
                results.append(OrderEstimationFailedDTO(message=f"Paths extraction failed for request {req}: {ex}"))
            except Exception as ex:
                logger.exception(f"Error processing request: {req}")
                results.append(OrderEstimationErrorDTO(message=f"Error during computation of realtime LCDI for request {req}: {ex}"))

        logger.debug("Finished processing realtime LCDI requests")

        if is_single:
            result: OrderEstimationResponseDTO = results[0]
            if isinstance(result, OrderEstimationCreatedDTO):
                return created_response(location_url=result.location, data=result.data)
            if isinstance(result, OrderEstimationFailedDTO):
                return unprocessable_entity_response(message=result.message)
            return internal_error_response(error_message=result.message)

        # Batch requests
        status_to_dto = {
            OrderEstimationCreatedDTO: OrderEstimationStatus.CREATED,
            OrderEstimationFailedDTO: OrderEstimationStatus.FAILED,
            OrderEstimationErrorDTO: OrderEstimationStatus.ERROR,
        }

        json_list: List[Dict] = []
        results_count: Dict[str, int] = defaultdict(int)

        for res in results:
            for dto_cls, status in status_to_dto.items():
                if isinstance(res, dto_cls):
                    json_list.append(res.model_dump())
                    results_count[status.value] += 1
                    break

        has_created = OrderEstimationStatus.CREATED.value in results_count
        has_failed = OrderEstimationStatus.FAILED.value in results_count
        has_error = OrderEstimationStatus.ERROR.value in results_count

        if sum([has_created, has_failed, has_error]) > 1:
            return multi_status_response(
                location_url=REALTIME_LCDI_PATH,
                data=json_list,
                add_location_header=has_created
            )

        if has_created:
            return created_response(location_url=REALTIME_LCDI_PATH, data=json_list)

        if has_failed:
            return unprocessable_entity_response(message="Realtime lcdi computation failed", data=json_list)

        return internal_error_response(error_message="Unexpected error during realtime lcdi computation", data=json_list)
    
    @app.post(f"{REALTIME_LCDI_PATH}/volatile")
    def handle_compute_volatile_realtime_lcdi() -> 'Response':
        payload: Dict[str, Any] = app.current_event.json_body
        logger.debug(f"Received payload for POST {REALTIME_LCDI_PATH}/volatile: {payload}")

        try:
            payload_parsed: VertexEstimationRequest = parse_as(VertexEstimationRequest, payload)  # type: ignore
        except ValidationError as e:
            logger.info(f"Invalid request body for POST {REALTIME_LCDI_PATH}: {e}")
            return bad_request_response(f"Invalid request body: {str(e)}")

        logger.debug(f"Parsed payload: {payload_parsed}")

        requests: List[VertexEstimationRequestDTO] = (
            [payload_parsed] if isinstance(payload_parsed, VertexEstimationRequestDTO)
            else payload_parsed.root
        )
        is_single: bool = isinstance(payload_parsed, VertexEstimationRequestDTO)

        bd_loader: BucketDataLoader = BucketDataLoader()
        
        sc_graph: SCGraph = bd_loader.load_sc_graph()
        logger.debug(f"SCGraph retrieved successfully")

        geo_service_lambda_client: GeoServiceLambdaClient = GeoServiceLambdaClient(
            lambda_arn=get_env(EXTERNAL_API_LAMBDA_ARN_KEY)
        )
        vertex_resolver: SCGraphResolver = SCGraphResolver(lambda_client=geo_service_lambda_client, maybe_sc_graph=sc_graph)
        logger.debug("Vertex resolver initialized")

        results: List[Dict[str, Any]] = []

        for req in requests:
            logger.debug(f"Processing request: {req}")
            try:
                v_dto: VertexDTO = req.vertex
                v_result: SCGraphVertexResult = vertex_resolver.resolve(v_dto)
                estimation = compute_volatile_realtime_lcdi(
                    vertex_estimation_request=req,
                    vertex=v_result.vertex,
                    sc_graph=sc_graph
                )
                results.append(estimation)
            except VertexNotFoundException as ex:
                logger.warning(f"Vertex not found for request {req}: {ex}")
                results.append({"message": f"Vertex not found for request {req}: {ex}"})
            except InvalidTimeSequenceException as ex:
                logger.warning(f"Invalid time sequence for request {req}: {ex}")
                results.append({"message":f"Invalid time sequence for request {req}: {ex}"})
            except ProbPathException as ex:
                logger.warning(f"Paths extraction failed for request {req}: {ex}")
                results.append({"message": f"Paths extraction failed for request {req}: {ex}"})
            except Exception as ex:
                logger.exception(f"Error processing request: {req}")
                results.append({"message": f"Error during computation of realtime LCDI for request {req}: {ex}"})

        logger.debug("Finished processing realtime LCDI requests")

        if is_single:
            result: Dict[str, Any] = results[0]
            if not "message" in result:
                return created_response(location_url="", data=result)
            if isinstance(result, OrderEstimationFailedDTO):
                return unprocessable_entity_response(message=result["message"])
            return internal_error_response(error_message=result["message"])

        return success_response(data=results)
