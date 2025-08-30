from typing import TYPE_CHECKING, List
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from datetime import datetime
    from sqs.dto.sqs_event_dto import SqsEventDataDTO, EventType
    from core.sc_graph.sc_graph_resolver import SCGraphResolver
    from sqs.dto.reconfiguration_dto import ReconfigurationEvent

class EventHandler(ABC):

    def __init__(self, sc_graph_resolver: 'SCGraphResolver') -> None:
        self.sc_graph_resolver: 'SCGraphResolver' = sc_graph_resolver

    @abstractmethod
    def handle(self, event_data: 'SqsEventDataDTO', timestamp: 'datetime') -> List['ReconfigurationEvent']:
        """
        Handle the incoming event and return a response.
        
        :param event: The event data to be processed.
        :return: A dictionary containing the response data.
        """
        pass

    @abstractmethod
    def get_event_type(self) -> 'EventType':
        """
        Get the type of the event this handler processes.
        
        :return: A string representing the event type.
        """
        pass