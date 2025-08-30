from dataclasses import dataclass, field

@dataclass(frozen=True)
class VertexTimeInputDTO:
    avg_ori: float = field(compare=True)