from typing import Optional, Dict, Any
from datetime import datetime, timezone

import igraph as ig

from graph_config import V_ID_ATTR, TYPE_ATTR

from service.db_utils import get_db_connector, get_read_only_db_connector
from service.db_connector import DBConnector
from service.read_only_db_connector import ReadOnlyDBConnector

from model.order import Order, OrderStatus
from model.vertex import VertexType
from model.site import Site
from model.carrier import Carrier
from model.alpha_opt import AlphaOpt

from core.serializer.bucket_data_loader import BucketDataLoader

from core.executor.tfst_executor import TFSTExecutor
from core.executor.executor import Executor, ExecutorResult

from core.initializer.alpha_initializer import AlphaInitializer
from core.initializer.tfst_initializer import TFSTInitializer, TFSTInitializerResult
from core.initializer.initializer import Initializer, InitializerResult

from core.query_handler.query_handler import QueryHandler
from core.query_handler.query_result import ShipmentTimeResult, DispatchTimeResult
from core.query_handler.params.params_result import ParamsResult
from core.query_handler.params.params_handler import ParamsHandler

from core.dto.time_sequence.time_sequence_dto import TimeSequenceInputDTO
from core.dto.dto_factory import DTOFactory

from core.sc_graph.sc_graph import SCGraph
from core.formatter.formatter import Formatter

from core.calculator.dt.dt_input_dto import DTInputDTO
from core.calculator.tfst.pt.pt_input_dto import PTBaseInputDTO
from core.calculator.tfst.tt.tt_input_dto import TTBaseInputDTO
from core.calculator.tfst.alpha.alpha_input_dto import AlphaBaseInputDTO
from core.calculator.time_deviation.time_deviation_input_dto import TimeDeviationBaseInputDTO 

from logger import get_logger
logger = get_logger(__name__)

def get_status(v: ig.Vertex, maybe_shipment_time: Optional[datetime]) -> OrderStatus:
    if v[TYPE_ATTR] == VertexType.MANUFACTURER.value:
        return OrderStatus.DELIVERED
    
    if maybe_shipment_time is None:
        return OrderStatus.PENDING
    
    return OrderStatus.IN_TRANSIT

def compute_order_realtime_lcdi(
        vertex: ig.Vertex,
        order_id: int,
        event_time: datetime,
        maybe_estimation_time: Optional[datetime] = None,
        maybe_sc_graph: Optional[SCGraph] = None,
        use_order_status: bool = True
        ) -> Dict[str, Any]:
    
    vertex_id: int = vertex[V_ID_ATTR]
    estimation_time: datetime = maybe_estimation_time or datetime.now(timezone.utc)

    bucket_loader: BucketDataLoader = BucketDataLoader()

    sc_graph: SCGraph = maybe_sc_graph or bucket_loader.load_sc_graph()
    logger.debug(f"SCGraph retrieved successfully")

    ro_db_connector: ReadOnlyDBConnector = get_read_only_db_connector()
    with ro_db_connector.session_scope() as session:
        query_handler: QueryHandler = QueryHandler(session=session)

        order: Order = query_handler.get_order(order_id=order_id)
        site: Site = order.site
        carrier: Carrier = order.carrier

        order_time: datetime = order.manufacturer_creation_timestamp
        maybe_shipment_time: Optional[datetime] = order.carrier_creation_timestamp   
        order_status: str = order.status if use_order_status else get_status(vertex, maybe_shipment_time).value

    logger.debug(f"Order data retrieved successfully: {order_time}")

    executor_result: ExecutorResult = compute_realtime_lcdi(
        sc_graph,
        site,
        carrier,
        vertex_id,
        order_time,
        event_time=event_time,
        estimation_time=estimation_time,
        maybe_shipment_time=maybe_shipment_time,
    )

    formatter: Formatter = Formatter()
    db_connector: DBConnector = get_db_connector()
    with db_connector.session_scope() as session:
        query_handler: QueryHandler = QueryHandler(session=session)
        et: int = query_handler.save_estimated_time(
            order_id=order_id,
            vertex_id=vertex_id,
            order_status=order_status,
            executor_result=executor_result
        )

        et_data: Dict[str, Any] = formatter.format_et(et)
    
    logger.debug(f"Successfully saved realtime lcdi record with ID: {et.id}")

    bucket_loader.save_dp_managers(sc_graph, force=False)

    return et_data

def compute_realtime_lcdi(
        sc_graph: SCGraph,
        site: Site,
        carrier: Carrier,
        vertex_id: int,
        order_time: datetime,
        event_time: datetime,
        estimation_time: datetime,
        maybe_shipment_time: Optional[datetime] = None,
        ) -> ExecutorResult:
    
    time_sequence_input: TimeSequenceInputDTO = TimeSequenceInputDTO(
        order_time=order_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    site_id: int = site.id
    
    dto_factory: DTOFactory = DTOFactory()
    ro_db_connector: ReadOnlyDBConnector = get_read_only_db_connector()
    
    with ro_db_connector.session_scope() as session:
        params_handler: ParamsHandler = ParamsHandler(session=session)
        params: ParamsResult = params_handler.get_params()
        logger.debug(f"Parameters retrieved successfully: {params}")

        query_handler: QueryHandler = QueryHandler(session=session)

        alpha_opt: AlphaOpt = query_handler.get_alpha_opt(site_id=site_id, carrier_id=carrier.id)
        logger.debug(f"Alpha optimal parameters retrieved successfully: {alpha_opt}")

        dispatch_time_result: DispatchTimeResult = query_handler.get_dispatch_time(site_id=site_id)
        logger.debug(f"Dispatch times retrieved successfully: {dispatch_time_result}")
        
        dt_input: DTInputDTO
        if maybe_shipment_time is not None:
            dt_input = dto_factory.create_dt_input_dto(
                site_id=site_id,
                maybe_shipment_time=maybe_shipment_time
            )
        else:
            dt_input = dto_factory.create_dt_input_dto(
                site_id=site_id,
                maybe_dispatch_time_result=dispatch_time_result
            )

        shipment_time_result: ShipmentTimeResult = query_handler.get_delivery_time(site_id=site_id, carrier_id=carrier.id)
        logger.debug(f"Delivery times retrieved successfully: {shipment_time_result}")

        alpha_base_input_dto: AlphaBaseInputDTO = dto_factory.create_alpha_base_input_dto(
            shipment_time_result=shipment_time_result,
            vertex_id=vertex_id
        )

        pt_base_input_dto: PTBaseInputDTO = dto_factory.create_pt_base_input_dto(
            vertex_id=vertex_id,
            carrier_names=[carrier.name]
        )
        
        tt_base_input_dto: TTBaseInputDTO = dto_factory.create_tt_base_input_dto(
            shipment_time_result=shipment_time_result
        ) 

        td_partial_input_dto: TimeDeviationBaseInputDTO = dto_factory.create_time_deviation_partial_input_dto(
            dispatch_time_result=dispatch_time_result,
            shipment_time_result=shipment_time_result
        )

    alpha_initializer: AlphaInitializer = AlphaInitializer(
        alpha_const_value=params.tfst_params.alpha_params.const_alpha_value,
        alpha_exp_tt_weight=alpha_opt.tt_weight
    )
        
    tfst_initializer: TFSTInitializer = TFSTInitializer(
        alpha_initializer=alpha_initializer,
        sc_graph=sc_graph
    )
    initializer: Initializer = Initializer(tfst_initializer)

    initializer_result: InitializerResult = initializer.initialize(
        params=params, 
        maybe_ro_db_connector=ro_db_connector
    )
    tfst_initializer_result: TFSTInitializerResult = initializer_result.tfst_initializer_result
    logger.debug(f"Calculators initialized successfully")

    tfst_executor: TFSTExecutor = TFSTExecutor(
        alpha_calculator=tfst_initializer_result.alpha_calculator,
        pt_calculator=tfst_initializer_result.pt_calculator,
        tt_calculator=tfst_initializer_result.tt_calculator,
        tfst_calculator=tfst_initializer_result.tfst_calculator,
        parallelization=params.parallelization,
        tolerance=params.tfst_params.tolerance
    )

    executor: Executor = Executor(
        dto_factory=dto_factory,
        dt_calculator=initializer_result.dt_calculator,
        tfst_calculator_executor=tfst_executor,
        est_calculator=initializer_result.est_calculator,
        cfdi_calculator=initializer_result.cfdi_calculator,
        eodt_calculator=initializer_result.eodt_calculator,
        edd_calculator=initializer_result.edd_calculator,
        td_calculator=initializer_result.time_deviation_calculator
    )

    executor_result: ExecutorResult = executor.execute(
        time_sequence_input=time_sequence_input,
        dt_input=dt_input,
        alpha_base_input=alpha_base_input_dto,   
        pt_base_input=pt_base_input_dto,
        tt_base_input=tt_base_input_dto,
        td_partial_input=td_partial_input_dto
    )
    logger.debug(f"Calculators executed successfully with parallelization: {params.parallelization}")

    return executor_result