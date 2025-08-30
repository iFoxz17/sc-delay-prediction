from dataclasses import dataclass, field

@dataclass(frozen=True)
class RouteTimeDTO:
    lower: float = field(metadata={"description": "Lower bound of the route time estimate in hours"})
    upper: float = field(metadata={"description": "Upper bound of the route time estimate in hours"})