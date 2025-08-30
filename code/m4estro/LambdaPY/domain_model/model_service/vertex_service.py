from typing import Dict, Any, List, Set, Optional
import igraph as ig

from service.lambda_client.geo_service_lambda_client import GeoServiceLambdaClient, LocationResult
from service.read_only_db_connector import ReadOnlyDBConnector
from service.db_utils import get_read_only_db_connector

from utils.config import EXTERNAL_API_LAMBDA_ARN_KEY, get_env, DATABASE_SECRET_ARN_KEY, AWS_REGION_KEY
from utils.parsing import parse_str_list
from graph_config import V_ID_ATTR, TYPE_ATTR

from serializer.s3_graph_serializer import S3GraphSerializer

from resolver.vertex_dto import VertexNameDTO
from resolver.vertex_not_found_exception import VertexNotFoundException
from resolver.vertex_resolver import VertexResolver, VertexResult

from model.vertex import Vertex, VertexType

from model_dto.q_params import VerticesQParamsKeys

from logger import get_logger
logger = get_logger(__name__)

def _get_vertex_data(vertex: ig.Vertex | Vertex) -> Dict[str, Any]:
    if isinstance(vertex, Vertex):
        return {
            "id": vertex.id,
            "name": vertex.name,
            "type": vertex.type.value,
        }
    
    return {
        "id": vertex[V_ID_ATTR],
        "name": vertex["name"],
        "type": vertex[TYPE_ATTR],
    }

def _initialize_resolver() -> VertexResolver:
    serializer: S3GraphSerializer = S3GraphSerializer()
    logger.debug(f"Serializer initialized successfully")

    graph: ig.Graph = serializer.deserialize()
    logger.debug(f"Graph deserialized successfully")

    lambda_client: GeoServiceLambdaClient = GeoServiceLambdaClient(lambda_arn=get_env(EXTERNAL_API_LAMBDA_ARN_KEY))
    logger.debug(f"External API Lambda client initialized successfully")

    resolver: VertexResolver = VertexResolver(graph=graph, lambda_client=lambda_client)
    logger.debug(f"Vertex resolver initialized")

    return resolver

def _resolve_vertices(vertex_names: Set[str], vertex_types: Set[VertexType]) -> List[Dict[str, Any]]:
    resolver = _initialize_resolver()
    resolved_vertices: List[Dict[str, Any]] = []

    for name in vertex_names:
        vertex: Optional[ig.Vertex] = _resolve_single_vertex(resolver, name, vertex_types)
        if vertex:
            resolved_vertices.append(_get_vertex_data(vertex))
        else:
            logger.warning(f"Could not resolve vertex with name '{name}' by types {vertex_types}. Skipping this vertex.")

    return resolved_vertices


def _resolve_single_vertex(resolver: VertexResolver, vertex_name: str, vertex_types: Set[VertexType]) -> Optional[ig.Vertex]:
    for vertex_type in vertex_types:
        logger.debug(f"Trying to resolve vertex with name '{vertex_name}' by type '{vertex_type}'")
        dto = VertexNameDTO(vertexName=vertex_name, vertexType=vertex_type)
        try:
            result: VertexResult = resolver.resolve(dto)
            logger.debug("Vertex resolved successfully")
            return result.vertex
        except VertexNotFoundException as e:
            logger.warning(f"Could not resolve vertex '{vertex_name}' by type '{vertex_type}'")
    
    return None

def _retrieve_vertices(vertex_types: Set[VertexType]) -> List[Dict[str, Any]]:
    ro_db_connector: ReadOnlyDBConnector = get_read_only_db_connector()
    logger.debug(f"Read-only DB connector initialized successfully")

    with ro_db_connector.session_scope() as session:
        query = session.query(Vertex)

        if vertex_types:
            logger.debug(f"Filtering vertices by types: {vertex_types}")
            query = query.filter(Vertex.type.in_([v_type.value for v_type in vertex_types]))
        
        vertices: List[Vertex] = query.all()
        logger.debug(f"Retrieved {len(vertices)} vertices from the database")

    return [_get_vertex_data(v) for v in vertices]


def get_vertices(q_params: Dict[str, str] = {}) ->  List[Dict[str, Any]]:
    vertex_names_raw: Set[str] = parse_str_list(q_params.get(VerticesQParamsKeys.NAME.value, ""), case='upper')
    logger.debug(f"Parsed raw vertex names from query parameters: {vertex_names_raw}")

    vertex_names: Set[str] = set([n.replace(";", ",").strip() for n in vertex_names_raw])
    logger.debug(f"Processed vertex names: {vertex_names}")

    vertex_types_raw: Set[str] = parse_str_list(q_params.get(VerticesQParamsKeys.TYPE.value, ""), case='upper')
    logger.debug(f"Parsed raw vertex types from query parameters: {vertex_types_raw}")
    
    vertex_types: Set[VertexType] = set()
    for t in vertex_types_raw:
        try:
            vertex_type: VertexType = VertexType(t)
            vertex_types.add(vertex_type)
        except ValueError:
            logger.warning(f"Invalid vertex type encountered: {t}. Skipping this type.")

    if vertex_names:
        if not vertex_types:
            if vertex_types_raw:
                logger.warning("No valid vertex types found in query parameters: returning empty list")
                return []
            logger.debug("No vertex types specified, using all available types")
            vertex_types = VertexType.get_all_types()

        logger.debug(f"Resolving {len(vertex_names)} vertices by name with types: {vertex_types}")
        return _resolve_vertices(vertex_names, vertex_types)

    # No vertex names provided: fall back to type-based retrieval
    if not vertex_types:
        if vertex_types_raw:
            logger.warning("No valid vertex types found in query parameters: returning empty list")
            return []
        logger.debug("No vertex types specified, using all available types")
        vertex_types = VertexType.get_all_types()

    logger.debug(f"Retrieving vertices with types {vertex_types} from db")
    return _retrieve_vertices(vertex_types)


def get_vertex_by_id(vertex_id: int) ->  Dict[str, Any]:
    ro_db_connector: ReadOnlyDBConnector = get_read_only_db_connector()
    logger.debug(f"Read-only DB connector initialized successfully")

    with ro_db_connector.session_scope() as session:
        maybe_vertex: Optional[Vertex] = session.query(Vertex).filter(Vertex.id == vertex_id).one_or_none()

    if not maybe_vertex:
        logger.warning(f"Vertex with ID {vertex_id} not found")
        raise VertexNotFoundException(f"Vertex with ID {vertex_id} not found")

    return _get_vertex_data(maybe_vertex)
    
