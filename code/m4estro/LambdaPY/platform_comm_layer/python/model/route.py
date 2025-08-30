from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import vertex
if TYPE_CHECKING:
    from model.vertex import Vertex

ROUTE_TABLE_NAME = 'routes'

class Route(Base):
    __tablename__ = ROUTE_TABLE_NAME
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"))
    source: Mapped["Vertex"] = relationship("Vertex", foreign_keys=[source_id])

    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"))
    destination: Mapped["Vertex"] = relationship("Vertex", foreign_keys=[destination_id])

    __table_args__ = (
        UniqueConstraint('source_id', 'destination_id', name='uq_route_source_destination'),
    )

    def __str__(self) -> str:
        return (f"Route(id={self.id}, source_id={self.source_id}, "
                f"destination_id={self.destination_id})")