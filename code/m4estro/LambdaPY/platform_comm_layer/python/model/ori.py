from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import vertex
if TYPE_CHECKING:
    from model.vertex import Vertex

ORI_TABLE_NAME = 'overall_residence_indices'

class ORI(Base):
    __tablename__ = ORI_TABLE_NAME
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    vertex_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"))
    vertex: Mapped["Vertex"] = relationship("Vertex")
    
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc))
    hours: Mapped[float] = mapped_column(Float)
    
    def __str__(self) -> str:
        return (f"ORI(id={self.id}, vertex_id={self.vertex_id} hours={self.hours})")