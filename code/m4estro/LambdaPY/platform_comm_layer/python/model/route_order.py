from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import vertex, order
if TYPE_CHECKING:
    from model.vertex import Vertex
    from model.order import Order

ROUTE_ORDER_TABLE_NAME = 'route_orders'

class RouteOrder(Base):
    __tablename__ = ROUTE_ORDER_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    source_id: Mapped[int] = mapped_column(ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"))
    source: Mapped["Vertex"] = relationship(foreign_keys=[source_id])

    destination_id: Mapped[int] = mapped_column(ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"))
    destination: Mapped["Vertex"] = relationship(foreign_keys=[destination_id])

    order_id: Mapped[int] = mapped_column(ForeignKey(f'{order.ORDER_TABLE_NAME}.id'))
    order: Mapped["Order"] = relationship("Order")

    __table_args__ = (
        UniqueConstraint('source_id', 'destination_id', 'order_id', name='uq_route_order_source_destination_order'),
    )

    def __str__(self) -> str:
        return (f"RouteOrder(id={self.id}, source_id={self.source_id}, "
                f"destination_id={self.destination_id}, order_id={self.order_id})")