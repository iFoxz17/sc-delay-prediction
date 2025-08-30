from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import order
if TYPE_CHECKING:
    from model.order import Order

ORDER_STEP_TABLE_NAME = 'order_steps'

class OrderStep(Base):
    __tablename__ = ORDER_STEP_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey(f"{order.ORDER_TABLE_NAME}.id"))
    order: Mapped["Order"] = relationship("Order")
    step: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    location: Mapped[str] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint('order_id', 'step', name='uq_order_step'),
    )

    def __str__(self) -> str:
        return (f"OrderStep(id={self.id}, order_id={self.order_id}, step={self.step}, "
                f"status={self.status}, timestamp={self.timestamp}, location={self.location})")
