from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import site, carrier

if TYPE_CHECKING:
    from model.site import Site
    from model.carrier import Carrier

SHIPMENT_TIME_GAMMA_TABLE_NAME = 'shipment_time_gammas'

class ShipmentTimeGamma(Base):
    __tablename__ = SHIPMENT_TIME_GAMMA_TABLE_NAME
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{site.SITE_TABLE_NAME}.id"))
    site: Mapped["Site"] = relationship("Site")
    
    carrier_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{carrier.CARRIER_TABLE_NAME}.id"))
    carrier: Mapped["Carrier"] = relationship("Carrier")
    
    shape: Mapped[float] = mapped_column(Float, nullable=False)
    loc: Mapped[float] = mapped_column(Float, nullable=False)
    scale: Mapped[float] = mapped_column(Float, nullable=False)
    skewness: Mapped[float] = mapped_column(Float, nullable=False)
    kurtosis: Mapped[float] = mapped_column(Float, nullable=False)
    mean: Mapped[float] = mapped_column(Float, nullable=False)
    std_dev: Mapped[float] = mapped_column(Float, nullable=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False)

    def __str__(self) -> str:
        return (f"ShipmentTimeGamma(id={self.id}, site_id={self.site_id}, carrier_id={self.carrier_id}, "
                f"shape={self.shape}, loc={self.loc}, scale={self.scale}, "
                f"skewness={self.skewness}, kurtosis={self.kurtosis}, "
                f"mean={self.mean}, std_dev={self.std_dev}, n={self.n})")