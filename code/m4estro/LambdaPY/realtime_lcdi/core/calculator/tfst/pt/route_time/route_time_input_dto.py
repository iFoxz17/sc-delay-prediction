from dataclasses import dataclass, field

from core.calculator.tfst.pt.tmi.tmi_dto import TMIValueDTO
from core.calculator.tfst.pt.wmi.wmi_dto import WMIValueDTO

@dataclass(frozen=True)
class RouteTimeInputDTO:
    latitude_source: float = field(compare=True)
    longitude_source: float = field(compare=True)

    latitude_destination: float = field(compare=True)
    longitude_destination: float = field(compare=True)

    distance: float = field(compare=True)

    tmi: TMIValueDTO = field(compare=True)
    avg_tmi: float = field(compare=True)

    wmi: WMIValueDTO = field(compare=True)
    avg_wmi: float = field(compare=True)

    avg_oti: float = field(compare=True)