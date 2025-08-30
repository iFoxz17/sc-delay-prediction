from typing import Dict, Any, TYPE_CHECKING

import igraph as ig

from graph_config import V_ID_ATTR

from service.db_utils import get_read_only_db_connector
from service.read_only_db_connector import ReadOnlyDBConnector

from core.serializer.bucket_data_loader import BucketDataLoader
from core.executor.executor import ExecutorResult
from core.calculator.tfst.pt.route_time.route_time_estimator import RouteTimeEstimator
from core.service.calculator_service import compute_realtime_lcdi, get_status
from core.query_handler.query_handler import QueryHandler
from core.sc_graph.sc_graph import SCGraph
from core.formatter.formatter import Formatter

from api.dto.vertex_estimation.vertex_estimation_request import VertexEstimationRequestDTO
from api.dto.carrier_dto import CarrierDTO, CarrierIdDTO, CarrierNameDTO

if TYPE_CHECKING:
    from model.site import Site
    from model.supplier import Supplier
    from model.carrier import Carrier
    from model.manufacturer import Manufacturer

from logger import get_logger
logger = get_logger(__name__)

def _get_carrier_from_request(query_handler: QueryHandler, carrier_dto: CarrierDTO) -> 'Carrier':
    if isinstance(carrier_dto, CarrierIdDTO):
        logger.debug(f"Retrieving Carrier by ID: {carrier_dto.carrier_id}")
        return query_handler.get_carrier(carrier_id=carrier_dto.carrier_id)
    elif isinstance(carrier_dto, CarrierNameDTO):
        logger.debug(f"Retrieving Carrier by Name: {carrier_dto.carrier_name}")
        return query_handler.get_carrier_by_name(carrier_name=carrier_dto.carrier_name)
    
    raise ValueError(f"Unsupported CarrierDTO type: {type(carrier_dto)}. Expected CarrierIdDTO or CarrierNameDTO.")


def compute_volatile_realtime_lcdi(
        vertex_estimation_request: VertexEstimationRequestDTO,
        vertex: ig.Graph,
        sc_graph: SCGraph,
        ) -> Dict[str, Any]:
        
    vertex_id: int = vertex[V_ID_ATTR]

    carrier_dto: CarrierDTO = vertex_estimation_request.carrier
    ro_db_connector: ReadOnlyDBConnector = get_read_only_db_connector()

    with ro_db_connector.session_scope() as session:
        query_handler: QueryHandler = QueryHandler(session=session)

        site: 'Site' = query_handler.get_site(site_id=vertex_estimation_request.site.site_id)
        supplier: 'Supplier' = site.supplier
        logger.debug(f"Site and supplier data retrieved successfully: {site}")
        
        carrier: 'Carrier' = _get_carrier_from_request(query_handler, carrier_dto)
        logger.debug(f"Carrier data retrieved successfully: {carrier}")

        manufacturer: 'Manufacturer' = query_handler.get_manufacturer()
        logger.debug(f"Manufacturer data retrieved successfully: {manufacturer}")
        
    executor_result: ExecutorResult = compute_realtime_lcdi(
        sc_graph,
        site,
        carrier,
        vertex_id,
        vertex_estimation_request.order_time,
        event_time=vertex_estimation_request.event_time,
        estimation_time=vertex_estimation_request.estimation_time,
        maybe_shipment_time=vertex_estimation_request.maybe_shipment_time
    )

    bucket_loader: BucketDataLoader = BucketDataLoader()
    bucket_loader.save_dp_managers(sc_graph, force=False)

    formatter: Formatter = Formatter()
    return formatter.format_volatile_result(
        vertex=vertex, 
        site=site, 
        supplier=supplier,
        carrier=carrier,
        manufacturer=manufacturer,
        executor_result=executor_result,
        status=get_status(vertex, vertex_estimation_request.maybe_shipment_time)
    )