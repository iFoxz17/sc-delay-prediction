from dataclasses import dataclass

@dataclass(frozen=True)
class TimeDeviationDTO:
    dt_td_lower: float
    dt_td_upper: float

    st_td_lower: float
    st_td_upper: float

    dt_confidence: float
    st_confidence: float

    @property
    def td_lower(self) -> float:
        return self.dt_td_lower + self.st_td_lower

    @property
    def td_upper(self) -> float:
        return self.dt_td_upper + self.st_td_upper