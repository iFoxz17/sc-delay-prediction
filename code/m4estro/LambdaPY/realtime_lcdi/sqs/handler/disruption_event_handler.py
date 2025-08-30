from typing import Dict, Any, List, override, TYPE_CHECKING
from datetime import datetime

from service.db_utils import get_read_only_db_connector

from model.vertex import VertexType

from resolver.vertex_dto import VertexDTO, VertexNameDTO

from core.sc_graph.sc_graph_resolver import SCGraphResolver, SCGraphVertexResult
from core.service.calculator_service import compute_order_realtime_lcdi

from sqs.handler.event_handler import EventHandler
from sqs.handler.event_query_handler import EventQueryHandler
from sqs.dto.sqs_event_dto import SqsEventDataDTO, EventType
from sqs.dto.disruption_event_dto import DisruptionEventDataDTO, DisruptionDTO, AffectedOrdersDTO
from sqs.dto.reconfiguration_dto import ReconfigurationEvent, ExternalDisruptionDTO

if TYPE_CHECKING:
    from model.order import Order
    from service.read_only_db_connector import ReadOnlyDBConnector
    
from logger import get_logger
logger = get_logger(__name__)

class DisruptionEventHandler(EventHandler):
    def __init__(self, sc_graph_resolver: SCGraphResolver) -> None:
        super().__init__(sc_graph_resolver)

    #TODO: implement this method to check if the order meets the criteria for delay computation
    def _meets_delay_computation_criteria(self, order_id: int, order_location: str) -> bool:
        return True  

    @override
    def handle(self, event_data: SqsEventDataDTO, timestamp: datetime) -> List[ReconfigurationEvent]:
        if not isinstance(event_data, DisruptionEventDataDTO):
            raise ValueError(f"Invalid event data type for DisruptionEventHandler: {type(event_data)}")

        disruption_event_data: DisruptionEventDataDTO = event_data
        event_timestamp: datetime = datetime.fromisoformat(disruption_event_data.event_timestamp)
        disruption_data: DisruptionDTO = disruption_event_data.disruption
        order_data: AffectedOrdersDTO = disruption_event_data.affected_orders
        
        if not "severity" in disruption_data.measurements:
            logger.warning(f"Disruption metadata missing 'severity' measurement, defaulting to 0.0")
            disruption_data.measurements["severity"] = 0.0
        
        external_disruption: ExternalDisruptionDTO = ExternalDisruptionDTO(
            disruptionType=disruption_data.disruption_type,
            severity=disruption_data.measurements["severity"]
        )

        order_ids: List[int] = order_data.summary.order_ids
        order_locations: List[str] = order_data.summary.locations

        if len(order_ids) != len(order_locations):
            logger.error(f"Order IDs and locations mismatch: {len(order_ids)} IDs vs {len(order_locations)} locations")
            raise ValueError("Order IDs and locations must match in length")

        reconfiguration_events: List[ReconfigurationEvent] = []

        for order_id, order_location in zip(order_ids, order_locations):
            logger.debug(f"Processing order ID {order_id} at location {order_location}")

            ro_db_connector: 'ReadOnlyDBConnector' = get_read_only_db_connector()
            with ro_db_connector.session_scope() as session:
                qh: EventQueryHandler = EventQueryHandler(session)
                try:
                    order: 'Order' = qh.get_order_by_id(order_id)
                except Exception:
                    logger.exception(f"Error fetching order with ID {order_id}: skipping delay computation")
                    reconfiguration_events.append(ReconfigurationEvent(
                        orderId=order_id,
                        SLS=False,
                        external=external_disruption,
                        delay=None
                    ))
                    continue    

            logger.debug(f"Order retrieved successfully from db: id={order.id}, order_status={order.status}")

            if not self._meets_delay_computation_criteria(order_id, order_location):
                logger.debug(f"Order at location {order_location} does not meet delay computation criteria, skipping delay computation")
                reconfiguration_events.append(ReconfigurationEvent(
                    orderId=order_id,
                    SLS=False,
                    external=external_disruption,
                    delay=None
                ))               
                continue

            vertex_dto: VertexDTO = VertexNameDTO(vertexName=str(order_location), vertexType=VertexType.INTERMEDIATE)
            logger.debug(f"Vertex DTO created: {vertex_dto}")     
            try:   
                vertex_result: SCGraphVertexResult = self.sc_graph_resolver.resolve(vertex_dto)
            except Exception:
                logger.exception(f"Error resolving vertex for order ID {order_id} at location {order_location}: skipping delay computation")
                reconfiguration_events.append(ReconfigurationEvent(
                    orderId=order_id,
                    SLS=order.SLS,
                    external=external_disruption,
                    delay=None
                ))
                continue
 
            et_data: Dict[str, Any] = compute_order_realtime_lcdi(
                vertex=vertex_result.vertex,
                order_id=order_id,
                event_time=event_timestamp,
                maybe_estimation_time=timestamp,
                maybe_sc_graph=vertex_result.sc_graph,
                use_order_status=True
            )
            logger.debug(f"Estimated time computed: {et_data}")

            reconfiguration_event: ReconfigurationEvent = ReconfigurationEvent.from_et(et_data, external=external_disruption, maybe_sls=order.SLS)
            reconfiguration_events.append(reconfiguration_event)

        return reconfiguration_events
    
    @override
    def get_event_type(self) -> EventType:
        return EventType.DISRUPTION_ALERT