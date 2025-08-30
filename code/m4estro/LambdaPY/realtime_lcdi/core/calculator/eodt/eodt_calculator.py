from datetime import datetime

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.est.est_dto import EST_DTO

from core.calculator.eodt.eodt_dto import EODT_DTO

from logger import get_logger
logger = get_logger(__name__)

class EODTCalculator:
    def __init__(self) -> None:
        pass

    def calculate(self, 
                  time_sequence: TimeSequenceDTO,
                  est: EST_DTO
                  ) -> EODT_DTO: 
        
        dispatch_elapsed_time: float = (time_sequence.shipment_time - time_sequence.order_time).total_seconds() / 3600.0
        shipment_elapsed_time: float = (time_sequence.shipment_estimation_time - time_sequence.shipment_time).total_seconds() / 3600.0

        eodt_value: float = dispatch_elapsed_time + shipment_elapsed_time + est.value
        return EODT_DTO(value=eodt_value)