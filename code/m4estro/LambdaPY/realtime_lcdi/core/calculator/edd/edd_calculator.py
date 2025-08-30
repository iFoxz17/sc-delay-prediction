from datetime import datetime, timedelta

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.eodt.eodt_dto import EODT_DTO
from core.calculator.edd.edd_dto import EDD_DTO

from logger import get_logger
logger = get_logger(__name__)

class EDDCalculator:
    def __init__(self) -> None:
        pass

    def calculate(self, time_sequence: TimeSequenceDTO, eodt: EODT_DTO) -> EDD_DTO: 
        edd_value: datetime = time_sequence.order_time + timedelta(hours=eodt.value)
        return EDD_DTO(value=edd_value)