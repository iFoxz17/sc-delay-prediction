from typing import Optional
from dataclasses import dataclass, field

from model.alpha import AlphaType

@dataclass(frozen=True)
class AlphaDTO:

    type_: AlphaType = field(
        metadata={"description": "Type of the Alpha calculation (CONST, EXP, MARKOV)"}
    )

    input: float = field(
        metadata={"description": "Input value for the Alpha calculation (max(0, t / AST))"}
    )

    value: float = field(
        metadata={"description": "Calculated Alpha value"}
    )

    maybe_tt_weight: Optional[float] = field(
        default=None,
        metadata={"description": "Travel time weight for EXP and MARKOV alpha calculations"}
    )

    maybe_tau: Optional[float] = field(
        default=None,
        metadata={"description": "Tau value for EXP and MARKOV alpha calculations"}
    )

    maybe_gamma: Optional[float] = field(
        default=None,
        metadata={"description": "Gamma value for EXP and MARKOV alpha calculations"}
    )    