from dataclasses import dataclass, field

@dataclass(frozen=True)
class VertexTimeDTO:
    lower: float = field(metadata={"description": "Lower bound of the vertex time estimate in hours"})
    upper: float = field(metadata={"description": "Upper bound of the vertex time estimate in hours"})