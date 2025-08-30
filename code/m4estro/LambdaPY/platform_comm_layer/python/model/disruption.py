from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import order, time_deviation
if TYPE_CHECKING:
    from model.order import Order
    from model.time_deviation import TimeDeviation

DISRUPTION_TABLE_NAME = 'disruptions'

class Disruption(Base):
    __tablename__ = DISRUPTION_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    order_id: Mapped[int] = mapped_column(ForeignKey(f'{order.ORDER_TABLE_NAME}.id'))
    order: Mapped["Order"] = relationship("Order")
    
    external: Mapped[bool] = mapped_column(Boolean, default=False)
    external_data: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    delayed: Mapped[bool] = mapped_column(Boolean, default=False)
    time_deviation_id: Mapped[Optional[int]] = mapped_column(ForeignKey(f'{time_deviation.TIME_DEVIATION_TABLE_NAME}.id'), nullable=True)
    time_deviation: Mapped[Optional["TimeDeviation"]] = relationship("TimeDeviation")
    
    message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    def __str__(self) -> str:
        return (f"Disruption(id={self.id}, order_id={self.order_id}, external={self.external}, "
                f"external_data={self.external_data}, delayed={self.delayed}, "
                f"time_deviation_id={self.time_deviation_id}, message={self.message})")