from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.eodt.eodt_calculator import EODTCalculator
from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.est.est_dto import EST_DTO
from core.calculator.eodt.eodt_dto import EODT_DTO

from core.calculator.dt.holiday.holiday_dto import HolidayResultDTO

def test_eodt_calculation():
    order_time = datetime(2025, 6, 21, 10, 0, 0, tzinfo=timezone.utc)
    shipment_time = order_time + timedelta(hours=96.0)
    event_time = shipment_time + timedelta(hours=1)
    estimation_time = event_time + timedelta(hours=1)
    
    time_sequence = TimeSequenceDTO(
        order_time=order_time,
        shipment_time=shipment_time,
        event_time=event_time,
        estimation_time=estimation_time
    )
    
    est = EST_DTO(value=24.0)

    calculator = EODTCalculator()
    result: EODT_DTO = calculator.calculate(
        time_sequence=time_sequence,
        est=est
    )

    # Expected EODT = DT + elapsed time + EST = 96.0 + 1.0 + 1.0 + 24.0 = 122.0 hours
    assert isinstance(result, EODT_DTO)
    assert result.value == (96.0 + 1.0 + 1.0 + 24.0)  # 122.0 hours
