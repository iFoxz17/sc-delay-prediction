from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import vertex
if TYPE_CHECKING:
    from model.vertex import Vertex

OTI_TABLE_NAME = 'overall_transit_indices'

class OTI(Base):
    __tablename__ = OTI_TABLE_NAME
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"))
    source: Mapped["Vertex"] = relationship("Vertex", foreign_keys=[source_id])
    
    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"))
    destination: Mapped["Vertex"] = relationship("Vertex", foreign_keys=[destination_id])
    
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc))
    hours: Mapped[float] = mapped_column(Float)

    def __str__(self) -> str:
        return (f"OTI(id={self.id}, source_id={self.source_id}, destination_id={self.destination_id}, "
                f"hours={self.hours})")