from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import vertex, estimated_time
if TYPE_CHECKING:
    from model.vertex import Vertex
    from model.estimated_time import EstimatedTime

WMI_TABLE_NAME = 'weather_meta_indices'

class WMI(Base):
    __tablename__ = WMI_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    estimated_time_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(f"{estimated_time.ESTIMATED_TIME_TABLE_NAME}.id")
    )
    estimated_time: Mapped[Optional["EstimatedTime"]] = relationship(foreign_keys=[estimated_time_id])
    
    source_id: Mapped[int] = mapped_column(ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"))
    source: Mapped["Vertex"] = relationship(foreign_keys=[source_id])
    
    destination_id: Mapped[int] = mapped_column(ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"))
    destination: Mapped["Vertex"] = relationship(foreign_keys=[destination_id])
    
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    
    n_interpolation_points: Mapped[int] = mapped_column(Integer, nullable=False)
    step_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    def __str__(self) -> str:
        return (f"WMI(id={self.id}, source_id={self.source_id}, "
                f"destination_id={self.destination_id}, created_at={self.created_at}, "
                f"timestamp={self.timestamp}, n_interpolation_points={self.n_interpolation_points}, "
                f"step_distance_km={self.step_distance_km}, value={self.value})")