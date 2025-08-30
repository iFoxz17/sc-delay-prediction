from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from sqlalchemy import Integer, Float, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from model.base import Base
from model import vertex, order, alpha, time_deviation, estimated_time_holiday, estimation_params
if TYPE_CHECKING:
    from model.vertex import Vertex
    from model.order import Order
    from model.alpha import Alpha
    from model.holiday import Holiday
    from time_deviation import TimeDeviation
    from estimation_params import EstimationParams
    
ESTIMATED_TIME_TABLE_NAME = 'estimated_times'

class EstimatedTime(Base):
    __tablename__ = ESTIMATED_TIME_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True)

    vertex_id: Mapped[int] = mapped_column(ForeignKey(f"{vertex.VERTEX_TABLE_NAME}.id"), nullable=False)
    vertex: Mapped["Vertex"] = relationship("Vertex")

    order_id: Mapped[int] = mapped_column(ForeignKey(f"{order.ORDER_TABLE_NAME}.id"), nullable=False)
    order: Mapped["Order"] = relationship("Order")

    shipment_time: Mapped[datetime] = mapped_column(nullable=False)
    event_time: Mapped[datetime] = mapped_column(nullable=False)
    estimation_time: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(nullable=False)
    
    DT_weekend_days: Mapped[int] = mapped_column(Integer, nullable=False)
    DT: Mapped[float] = mapped_column(Float, nullable=False)
    DT_lower: Mapped[float] = mapped_column(Float, nullable=False)
    DT_upper: Mapped[float] = mapped_column(Float, nullable=False)
    TT_lower: Mapped[float] = mapped_column(Float, nullable=False)
    TT_upper: Mapped[float] = mapped_column(Float, nullable=False)
    PT_n_paths: Mapped[int] = mapped_column(Integer, nullable=False)
    PT_avg_tmi: Mapped[float] = mapped_column(Float, nullable=False)
    PT_avg_wmi: Mapped[float] = mapped_column(Float, nullable=False)
    PT_lower: Mapped[float] = mapped_column(Float, nullable=False)
    PT_upper: Mapped[float] = mapped_column(Float, nullable=False)
    TFST_lower: Mapped[float] = mapped_column(Float, nullable=False)
    TFST_upper: Mapped[float] = mapped_column(Float, nullable=False)
    EST: Mapped[float] = mapped_column(Float, nullable=False)
    EODT: Mapped[float] = mapped_column(Float, nullable=False)
    CFDI_lower: Mapped[float] = mapped_column(Float, nullable=False)
    CFDI_upper: Mapped[float] = mapped_column(Float, nullable=False)
    EDD: Mapped[datetime] = mapped_column(nullable=False)

    time_deviation_id: Mapped[int] = mapped_column(ForeignKey(f"{time_deviation.TIME_DEVIATION_TABLE_NAME}.id"), nullable=False)
    time_deviation: Mapped["TimeDeviation"] = relationship("TimeDeviation")

    alpha_id: Mapped[int] = mapped_column(ForeignKey(f"{alpha.ALPHA_TABLE_NAME}.id"), nullable=False)
    alpha: Mapped["Alpha"] = relationship("Alpha")

    estimation_params_id: Mapped[int] = mapped_column(ForeignKey(f"{estimation_params.ESTIMATION_PARAMS_TABLE_NAME}.id"), nullable=False)
    estimation_params: Mapped["EstimationParams"] = relationship("EstimationParams")

    holidays: Mapped[List["Holiday"]] = relationship(
        "Holiday",
        secondary=estimated_time_holiday.ESTIMATED_TIME_HOLIDAY_TABLE_NAME
    )

    def __str__(self) -> str:
        return (f"EstimatedTime(id={self.id}, vertex_id={self.vertex_id}, order_id={self.order_id}, "
                f"shipment_time={self.shipment_time}, event_time={self.event_time}, "
                f"estimation_time={self.estimation_time}, status={self.status}, "
                f"DT_weekend_days={self.DT_weekend_days}, DT={self.DT}, "
                f"TT_lower={self.TT_lower}, TT_upper={self.TT_upper}, "
                f"PT_n_paths={self.PT_n_paths}, PT_avg_tmi={self.PT_avg_tmi}, "
                f"PT_avg_wmi={self.PT_avg_wmi}, PT_lower={self.PT_lower}, PT_upper={self.PT_upper}, "
                f"TFST_lower={self.TFST_lower}, TFST_upper={self.TFST_upper}, "
                f"EST={self.EST}, EODT={self.EODT}, CFDI_lower={self.CFDI_lower}, CFDI_upper={self.CFDI_upper}, "
                f"EDD={self.EDD}, time_deviation_id={self.time_deviation_id}, alpha_id={self.alpha_id}, "
                f"estimation_params_id={self.estimation_params_id})")
