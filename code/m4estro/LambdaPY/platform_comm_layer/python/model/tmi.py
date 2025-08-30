from datetime import datetime, timezone
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum

from model.base import Base
from model import vertex, estimated_time
if TYPE_CHECKING:
    from model.vertex import Vertex
    from model.estimated_time import EstimatedTime

class TransportationMode(Enum):
    AIR = "AIR"
    RAIL = "RAIL"
    ROAD = "ROAD"
    SEA = "SEA"
    UNKNOWN = "UNKNOWN"

TMI_TABLE_NAME = 'traffic_meta_indices'

class TMI(Base):
    __tablename__ = TMI_TABLE_NAME
    
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
    
    transportation_mode: Mapped[TransportationMode] = mapped_column(
        SQLEnum(TransportationMode, name='transportation_mode_enum', native_enum=False),
        nullable=False
    )
    
    value: Mapped[float] = mapped_column(Float, nullable=False)

    def __str__(self) -> str:
        return (f"TMI(id={self.id}, estimated_time_id={self.estimated_time_id}, "
                f"source_id={self.source_id}, destination_id={self.destination_id}, "
                f"created_at={self.created_at}, timestamp={self.timestamp}, "
                f"transportation_mode={self.transportation_mode}, value={self.value})")