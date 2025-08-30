from typing import List
from dataclasses import dataclass, field

from core.query_handler.params.params_result import PTParams

from core.calculator.tfst.pt.tmi.tmi_dto import TMI_DTO
from core.calculator.tfst.pt.wmi.wmi_dto import WMI_DTO

@dataclass(frozen=True)
class PT_DTO:
    lower: float = field(metadata={"description": "Lower bound of the PT (Path Time) estimate in hours"})
    upper: float = field(metadata={"description": "Upper bound of the PT (Path Time) estimate in hours"})

    n_paths: int = field(metadata={"description": "Number of paths considered in the PT estimate"})
    avg_wmi: float = field(metadata={"description": "Weighted average of the WMIs for the routes of the first vertex"})
    avg_tmi: float = field(metadata={"description": "Weighted average of the TMIs for the routes of the first vertex"}) 

    params: PTParams = field(metadata={"description": "Parameters used for the PT calculation"})

    tmi_data: List[TMI_DTO] = field(default_factory=list, metadata={"description": "List of TMI computed for the paths"})
    wmi_data: List[WMI_DTO] = field(default_factory=list, metadata={"description": "List of WMI computed for the paths"})

    