from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import order, location
if TYPE_CHECKING:
    from model.order import Order
    from model.location import Location

ORDER_STEP_ENRICHED_TABLE_NAME = 'order_steps_enriched'

class OrderStepEnriched(Base):
    __tablename__ = ORDER_STEP_ENRICHED_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    order_id: Mapped[int] = mapped_column(ForeignKey(f"{order.ORDER_TABLE_NAME}.id"))
    order: Mapped["Order"] = relationship("Order")
    
    step_source: Mapped[int] = mapped_column(nullable=False)
    timestamp_source: Mapped[datetime] = mapped_column(nullable=False)
    location_name_source: Mapped[str] = mapped_column(ForeignKey(f"{location.LOCATION_TABLE_NAME}.name"))
    location_source: Mapped["Location"] = relationship(
        primaryjoin="OrderStepEnriched.location_name_source == Location.name",
        foreign_keys=[location_name_source],
        uselist=False
    )

    step_destination: Mapped[int] = mapped_column(nullable=False)
    timestamp_destination: Mapped[datetime] = mapped_column(nullable=False)
    location_name_destination: Mapped[str] = mapped_column(ForeignKey(f"{location.LOCATION_TABLE_NAME}.name"))
    location_destination: Mapped["Location"] = relationship(
        primaryjoin="OrderStepEnriched.location_name_destination == Location.name",
        foreign_keys=[location_name_destination],
        uselist=False
    )

    hours: Mapped[float] = mapped_column(nullable=False)
    geodesic_km: Mapped[float] = mapped_column(nullable=False)
    distance_road_km: Mapped[float] = mapped_column(nullable=False)
    time_road_no_traffic_hours: Mapped[float] = mapped_column(nullable=False)
    time_road_traffic_hours: Mapped[float] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint('order_id', 'step_source', name='uq_order_step_source'),
    )

    def __str__(self) -> str:
        return (f"OrderStepEnriched(id={self.id}, order_id={self.order_id}, "
                f"step_source={self.step_source}, timestamp_source={self.timestamp_source}, "
                f"location_name_source={self.location_name_source}, step_destination={self.step_destination}, "
                f"timestamp_destination={self.timestamp_destination}, "
                f"location_name_destination={self.location_name_destination}, hours={self.hours}, "
                f"geodesic_km={self.geodesic_km}, distance_road_km={self.distance_road_km}, "
                f"time_road_no_traffic_hours={self.time_road_no_traffic_hours}, "
                f"time_road_traffic_hours={self.time_road_traffic_hours})")