from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base

TIME_DEVIATION_TABLE_NAME = 'time_deviations'

class TimeDeviation(Base):
    __tablename__ = TIME_DEVIATION_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    dt_hours_lower: Mapped[float] = mapped_column(nullable=False)
    dt_hours_upper: Mapped[float] = mapped_column(nullable=False)

    st_hours_lower: Mapped[float] = mapped_column(nullable=False)
    st_hours_upper: Mapped[float] = mapped_column(nullable=False)

    dt_confidence: Mapped[float] = mapped_column(nullable=False)
    st_confidence: Mapped[float] = mapped_column(nullable=False)

    def __str__(self) -> str:
        return (f"TimeDeviation(id={self.id}, "
                f"dt_hours_lower={self.dt_hours_lower}, "
                f"dt_hours_upper={self.dt_hours_upper}, "
                f"st_hours_lower={self.st_hours_lower}, "
                f"st_hours_upper={self.st_hours_upper}, "
                f"dt_confidence={self.dt_confidence}, "
                f"st_confidence={self.st_confidence})")