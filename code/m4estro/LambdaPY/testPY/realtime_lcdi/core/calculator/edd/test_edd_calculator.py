from datetime import datetime, timezone, timedelta

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.calculator.edd.edd_calculator import EDDCalculator
from core.calculator.edd.edd_dto import EDD_DTO
from core.calculator.eodt.eodt_dto import EODT_DTO


def test_edd_calculation():
    order_time = datetime(2025, 6, 21, 10, 0, 0, tzinfo=timezone.utc)
    shipment_time = order_time + timedelta(hours=2)
    event_time = shipment_time + timedelta(hours=1)
    estimation_time = event_time + timedelta(hours=1)

    time_sequence = TimeSequenceDTO(
        order_time=order_time,
        shipment_time=shipment_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    eodt = EODT_DTO(value=36.0)  # 36 hours later

    calculator = EDDCalculator()
    result: EDD_DTO = calculator.calculate(time_sequence=time_sequence, eodt=eodt)

    expected_edd = order_time + timedelta(hours=36)

    assert isinstance(result, EDD_DTO)
    assert result.value == expected_edd
