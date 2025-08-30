from typing import Dict, Any, Set, List, Optional
import igraph as ig
from sqlalchemy import func

from utils.parsing import parse_str_list, parse_id_list
from service.lambda_client.geo_service_lambda_client import GeoServiceLambdaClient

from graph_config import V_ID_ATTR

from service.read_only_db_connector import ReadOnlyDBConnector
from service.db_utils import get_read_only_db_connector

from utils.config import EXTERNAL_API_LAMBDA_ARN_KEY, get_env

from api.dto.qparam import PathQParamKeys
from api.exception.bad_vertex_ids_exception import BadVertexIdsException
from api.exception.bad_carrier_names_exception import BadCarrierNamesException

from model.carrier import Carrier

from resolver.vertex_dto import VertexIdDTO
from resolver.vertex_not_found_exception import VertexNotFoundException

from core.sc_graph.utils import VertexIdentifier
from core.serializer.bucket_data_loader import BucketDataLoader

from core.sc_graph.sc_graph_resolver import SCGraphResolver, SCGraphVertexResult
from core.sc_graph.sc_graph import SCGraph
from core.dto.path.paths_dto import PathsIdDTO, PathsNameDTO

from logger import get_logger
logger = get_logger(__name__)

def get_prob_paths(qparams: Dict[str, Any]) -> List[PathsIdDTO | PathsNameDTO]:
    source_ids_raw: str = qparams.get(PathQParamKeys.SOURCE.value, "")
    logger.debug(f"Raw source IDs from query parameters: {source_ids_raw}")

    maybe_source_ids: Optional[Set[int]] = parse_id_list(source_ids_raw) if source_ids_raw else None
    logger.debug(f"Parsed source IDs from query parameters: {maybe_source_ids}")

    carrier_names_raw: str = qparams.get(PathQParamKeys.CARRIER_NAME.value, "")
    logger.debug(f"Raw carrier names from query parameters: {carrier_names_raw}")

    maybe_carrier_names: Optional[Set[str]] = set(parse_str_list(carrier_names_raw)) if carrier_names_raw else None
    logger.debug(f"Parsed carrier names from query parameters: {maybe_carrier_names}")

    maybe_by: Optional[str] = qparams.get(PathQParamKeys.BY.value, None)
    by: VertexIdentifier = VertexIdentifier.from_str(maybe_by) if maybe_by else VertexIdentifier.NAME
    logger.debug(f"Using vertex identifier: {by}")

    bucket_data_loader: BucketDataLoader = BucketDataLoader()
    sc_graph: SCGraph = bucket_data_loader.load_sc_graph()
    logger.debug("SCGraph loaded successfully")

    geo_service_lambda_client: GeoServiceLambdaClient = GeoServiceLambdaClient(
        lambda_arn=get_env(EXTERNAL_API_LAMBDA_ARN_KEY)
    )
    vertex_resolver: SCGraphResolver = SCGraphResolver(lambda_client=geo_service_lambda_client, maybe_sc_graph=sc_graph)
    logger.debug("Vertex resolver initialized")

    if not maybe_source_ids:
        if source_ids_raw:
            logger.debug(f"No valid source ID provided")
            raise BadVertexIdsException(bad_ids=source_ids_raw)

        source_ids: Set[int] = set([v[V_ID_ATTR] for v in sc_graph.graph.vs])
        logger.debug("No source IDs provided, using all vertices in the graph.")
    else:
        source_ids: Set[int] = maybe_source_ids
        logger.debug(f"Using provided source IDs: {source_ids}")

    if not maybe_carrier_names:
        logger.debug("No carrier names provided, using all carriers with at least one order.")
        ro_db_connector: ReadOnlyDBConnector = get_read_only_db_connector()
        with ro_db_connector.session_scope() as session:
            carrier_names: List[str] = [c.name for c in session.query(Carrier).filter(Carrier.n_orders > 0).all()]
    else:
        logger.debug(f"Using provided carrier names: {maybe_carrier_names}")
        ro_db_connector: ReadOnlyDBConnector = get_read_only_db_connector()
        with ro_db_connector.session_scope() as session:
            carrier_names: List[str] = [c.name for c in session.query(Carrier).filter(func.lower(Carrier.name).in_(maybe_carrier_names)).all()]

        if not carrier_names:
            logger.debug("No valid carrier name found.")
            raise BadCarrierNamesException(bad_names=carrier_names_raw)
    
    logger.debug(f"Carrier names resolved successfully: {carrier_names}")    
    
    all_paths: List[PathsIdDTO | PathsNameDTO] = []
    for source_id in source_ids:
        logger.debug(f"Resolving vertex with ID: {source_id}")
        v_dto: VertexIdDTO = VertexIdDTO(vertexId=source_id)
        try:
            v_result: SCGraphVertexResult = vertex_resolver.resolve(v_dto)
        except VertexNotFoundException as e:
            logger.warning(f"Vertex with ID {source_id} not found in the graph: {e}")
            continue

        v: ig.Vertex = v_result.vertex
        logger.debug(f"Vertex resolved successfully: {v}")

        paths: PathsIdDTO | PathsNameDTO = sc_graph.extract_paths(
            source=v,
            carriers=carrier_names,
            zero_prob_paths=False,
            by=by
        )

        logger.debug(f"Extracted paths for source vertex {v[V_ID_ATTR]}: {paths}")
        all_paths.append(paths)

    bucket_data_loader.save_dp_managers(sc_graph, force=False)

    return all_paths 