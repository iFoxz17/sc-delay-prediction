from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import site, carrier
if TYPE_CHECKING:
    from model.site import Site
    from model.carrier import Carrier

SHIPMENT_TIME_TABLE_NAME = 'shipment_times'

class ShipmentTime(Base):
    __tablename__ = SHIPMENT_TIME_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    site_id: Mapped[int] = mapped_column(ForeignKey(f"{site.SITE_TABLE_NAME}.id"))
    site: Mapped["Site"] = relationship("Site")

    carrier_id: Mapped[int] = mapped_column(ForeignKey(f"{carrier.CARRIER_TABLE_NAME}.id"))
    carrier: Mapped["Carrier"] = relationship("Carrier")
    
    hours: Mapped[float] = mapped_column(Float, nullable=False)

    def __str__(self) -> str:
        return (f"ShipmentTime(id={self.id}, site_id={self.site_id}, "
                f"carrier_id={self.carrier_id}, hours={self.hours})")