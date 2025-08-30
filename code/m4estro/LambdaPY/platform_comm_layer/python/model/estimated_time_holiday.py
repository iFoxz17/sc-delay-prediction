from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from model.holiday import HOLIDAYS_TABLE_NAME
from model.base import Base

ESTIMATED_TIME_HOLIDAY_TABLE_NAME = 'estimated_times_holidays'

class EstimatedTimeHoliday(Base):
    __tablename__ = ESTIMATED_TIME_HOLIDAY_TABLE_NAME

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    estimated_time_id: Mapped[int] = mapped_column(Integer, ForeignKey("estimated_times.id"), nullable=False)

    holiday_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{HOLIDAYS_TABLE_NAME}.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint('estimated_time_id', 'holiday_id', name='uq_estimated_time_holiday'),
    )

    def __str__(self) -> str:
        return (f"EstimatedTimeHoliday(id={self.id}, "
                f"estimated_time_id={self.estimated_time_id}, "
                f"holiday_id={self.holiday_id})")
