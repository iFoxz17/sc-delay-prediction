from sqlalchemy import Integer, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import and_
from typing import Optional, TYPE_CHECKING

from model.base import Base
from model import order, order_step_enriched
if TYPE_CHECKING:
    from model.order_step_enriched import OrderStepEnriched

WEATHER_DATA_TABLE_NAME = 'weather_data'

class WeatherData(Base):
    __tablename__ = WEATHER_DATA_TABLE_NAME
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{order.ORDER_TABLE_NAME}.id"))
    order_step_source: Mapped[int] = mapped_column(Integer)
    
    order_step_enriched: Mapped[Optional["OrderStepEnriched"]] = relationship(
        "OrderStepEnriched",
        primaryjoin=and_(
            order_step_enriched.OrderStepEnriched.order_id == order_id,
            order_step_enriched.OrderStepEnriched.step_source == order_step_source
        ),
        foreign_keys=[order_id, order_step_source],
        uselist=False
    )

    interpolation_step: Mapped[int] = mapped_column(Integer)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    step_distance_km: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[str] = mapped_column(String)
    weather_codes: Mapped[str] = mapped_column(String)
    temperature_celsius: Mapped[float] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint('order_id', 'order_step_source', 'interpolation_step', name='uq_order_step_interpolation'),
    )

    def __str__(self) -> str:
        return (f"WeatherData(id={self.id}, order_id={self.order_id}, "
                f"order_step_source={self.order_step_source}, interpolation_step={self.interpolation_step}, "
                f"latitude={self.latitude}, longitude={self.longitude}, "
                f"step_distance_km={self.step_distance_km}, timestamp={self.timestamp}, "
                f"weather_codes={self.weather_codes}, temperature_celsius={self.temperature_celsius})")