import json
from typing import Dict, TYPE_CHECKING, List, Optional, Any

from utils.parsing import parse_as
from utils.config import EXTERNAL_API_LAMBDA_ARN_KEY, RECONFIGURATION_QUEUE_URL_KEY, get_env

from service.sqs_client.sqs_client import SqsClient
from service.lambda_client.geo_service_lambda_client import GeoServiceLambdaClient

from core.sc_graph.sc_graph_resolver import SCGraphResolver

from sqs.dto.sqs_event_dto import SqsEvent, EventType
from sqs.dto.reconfiguration_dto import ReconfigurationEvent, DelayDTO, ExternalDisruptionDTO

from sqs.handler.event_handler import EventHandler
from sqs.handler.disruption_event_handler import DisruptionEventHandler
from sqs.handler.order_event_handler import OrderEventHandler

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

from logger import get_logger
logger = get_logger(__name__)


def _extract_body(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    if 'Records' in event:
        return [json.loads(record['body']) for record in event['Records']]
    elif 'body' in event:
        return [json.loads(event['body'])]
    else:
        raise ValueError("Event must contain 'Records' or 'body' key")

def _get_event_handlers(resolver: SCGraphResolver) -> Dict[EventType, EventHandler]:
    return {
        EventType.TRACKING_EVENT: OrderEventHandler(resolver),
        EventType.DISRUPTION_ALERT: DisruptionEventHandler(resolver),
    }

def _meets_forwarding_criteria(event: ReconfigurationEvent) -> bool:
    sls: bool = event.sls
    if sls:
        logger.debug("Found SLS true in event, forwarding to queue.")
        return True
    
    external: Optional[ExternalDisruptionDTO] = event.external
    if external is not None:
        logger.debug("Found external disruption in event, forwarding to queue.")
        return True
    
    delay: Optional[DelayDTO] = event.delay
    if delay is not None:
        if delay.total_lower > 0 or delay.total_upper > 0:
            logger.debug("Found positive delay in event, forwarding to queue.")
            return True
        
        logger.debug("Found not positive delay in event, not forwarding to queue.")
    
    logger.debug("No conditions met for forwarding event to queue.")
    return False

def handler(event: Dict[str, Any], context: 'LambdaContext') -> None:
    logger.debug(f"Received raw event: {json.dumps(event)}")

    try:
        extracted_events: List[Dict[str, Any]] = _extract_body(event)
    except Exception as e:
        logger.error(f"Failed to extract body: {e}")
        return

    logger.debug(f"Extracted {len(extracted_events)} events.")
    
    geo_service_client: GeoServiceLambdaClient = GeoServiceLambdaClient(lambda_arn=get_env(EXTERNAL_API_LAMBDA_ARN_KEY))
    logger.debug(f"Initialized GeoServiceLambdaClient with ARN: {get_env(EXTERNAL_API_LAMBDA_ARN_KEY)}")

    sqs_client: SqsClient = SqsClient(queue_url=get_env(RECONFIGURATION_QUEUE_URL_KEY))
    logger.debug(f"Initialized SQS client with queue URL: {get_env(RECONFIGURATION_QUEUE_URL_KEY)}")

    resolver: SCGraphResolver = SCGraphResolver(lambda_client=geo_service_client)
    logger.debug("Initialized SCGraphResolver.")

    handlers: Dict[EventType, EventHandler] = _get_event_handlers(resolver)
    logger.debug("Initialized event handlers for tracking and disruption events.")

    for raw_event in extracted_events:
        try:
            parsed_event: SqsEvent = parse_as(SqsEvent, raw_event)
        except Exception as e:
            logger.error(f"Failed to parse SqsEvent: {e}")
            continue

        logger.debug(f"Processing event type: {parsed_event.event_type}")
        handler_instance: Optional[EventHandler] = handlers.get(parsed_event.event_type)
        if not handler_instance:
            logger.error(f"Unsupported event type: {parsed_event.event_type}")
            continue

        try:
            reconfig_events: List[ReconfigurationEvent] = handler_instance.handle(parsed_event.data, parsed_event.timestamp)
            logger.debug(f"Returned {len(reconfig_events)} reconfiguration events from handler for {parsed_event.event_type}.")
            for reconfig_event in reconfig_events:
                logger.debug(f"Processing reconfiguration event: {reconfig_event}")
                if _meets_forwarding_criteria(reconfig_event):
                    sqs_client.send_message(reconfig_event.model_dump(by_alias=True))
        except Exception as e:
            logger.error(f"Error handling {parsed_event.event_type}: {e}")
            continue

    logger.debug("Finished processing all events.")
