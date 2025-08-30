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
from sqs.dto.order_event_dto import OrderEventDataDTO, OrderEventType
from sqs.dto.reconfiguration_dto import ReconfigurationEvent

if TYPE_CHECKING:
    from model.order import Order
    from service.read_only_db_connector import ReadOnlyDBConnector

from logger import get_logger
logger = get_logger(__name__)

class OrderEventHandler(EventHandler):
    def __init__(self, sc_graph_resolver: SCGraphResolver) -> None:
        super().__init__(sc_graph_resolver)

    @override
    def handle(self, event_data: SqsEventDataDTO, timestamp: datetime) -> List[ReconfigurationEvent]:
        if not isinstance(event_data, OrderEventDataDTO):
            raise ValueError(f"Invalid event data type for OrderEventHandler: {type(event_data)}")
        
        order_event_data: OrderEventDataDTO = event_data
        order_event_type: OrderEventType = order_event_data.type_

        ro_db_connector: 'ReadOnlyDBConnector' = get_read_only_db_connector()
        with ro_db_connector.session_scope() as session:
            qh: EventQueryHandler = EventQueryHandler(session)
            try:
                order: 'Order' = qh.get_order_by_id(order_event_data.order_id)
            except Exception as e:
                logger.exception(f"Error fetching order with ID {order_event_data.order_id}")
                raise ValueError(f"Order not found for ID {order_event_data.order_id}") from e
            
        logger.debug(f"Order retrieved successfully: id={order.id}, order_status={order.status}")

        reconfiguration_events: List[ReconfigurationEvent] = []
        for new_timestamp_str, _, new_location in zip(
            order_event_data.event_timestamps,
            order_event_data.order_new_steps_ids,
            order_event_data.order_new_locations
        ):  
            logger.debug(f"Processing new event: timestamp={new_timestamp_str}, location={new_location}")
            try:
                new_timestamp: datetime = datetime.fromisoformat(new_timestamp_str)
            except ValueError as e:
                logger.exception(f"Could not parse timestamp: {new_timestamp_str}: skipping event")
                continue
            
            vertex_dto: VertexDTO = self._build_vertex_dto_from_order(order_event_type, new_location, order)
            logger.debug(f"Vertex DTO created: {vertex_dto}")

            vertex_result: SCGraphVertexResult = self.sc_graph_resolver.resolve(vertex_dto)

            et_data: Dict[str, Any] = compute_order_realtime_lcdi(
                vertex=vertex_result.vertex,
                order_id=order.id,
                event_time=new_timestamp,
                maybe_estimation_time=timestamp,
                maybe_sc_graph=vertex_result.sc_graph,
                use_order_status=True
            )
            logger.debug(f"Estimated time computed: {et_data}")

            reconfiguration_event: ReconfigurationEvent = ReconfigurationEvent.from_et(et_data, maybe_sls=order.SLS)
            logger.debug(f"Reconfiguration event created: {reconfiguration_event}")
            reconfiguration_events.append(reconfiguration_event)

        logger.debug(f"Created {len(reconfiguration_events)} reconfiguration events for order {order.id}")
        return reconfiguration_events

    def _build_vertex_dto_from_order(self, type_: OrderEventType, event_location: str, order: 'Order') -> VertexDTO:
        match type_:
            case OrderEventType.ORDER_CREATION | OrderEventType.CARRIER_CREATION:
                logger.debug(f"Handling {type_.name} event")
                return VertexNameDTO(
                    vertexName=str(order.site_id),
                    vertexType=VertexType.SUPPLIER_SITE
                )

            case OrderEventType.CARRIER_UPDATE:
                logger.debug("Handling carrier update event")
                return VertexNameDTO(
                    vertexName=str(event_location),
                    vertexType=VertexType.INTERMEDIATE
                )

            case OrderEventType.CARRIER_DELIVERY:
                logger.debug("Handling carrier delivery event")
                return VertexNameDTO(
                    vertexName=str(order.manufacturer.name),
                    vertexType=VertexType.MANUFACTURER
                )

            case _:
                logger.error(f"Unknown carrier event type: {type_}")
                raise ValueError(f"Unsupported carrier event type: {type_}")

    @override
    def get_event_type(self) -> EventType:
        return EventType.TRACKING_EVENT