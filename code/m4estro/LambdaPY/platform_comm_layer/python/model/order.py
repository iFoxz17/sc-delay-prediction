from typing import Dict, Any
from enum import Enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import manufacturer, site, carrier
if TYPE_CHECKING:
    from model.manufacturer import Manufacturer
    from model.site import Site
    from model.carrier import Carrier

class OrderStatus(Enum):
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"

ORDER_TABLE_NAME = 'orders'

class Order(Base):
    __tablename__ = ORDER_TABLE_NAME

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    manufacturer_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{manufacturer.MANUFACTURER_TABLE_NAME}.id"), nullable=False)
    manufacturer: Mapped["Manufacturer"] = relationship("Manufacturer")
    
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{site.SITE_TABLE_NAME}.id"), nullable=False)
    site: Mapped["Site"] = relationship("Site")

    carrier_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{carrier.CARRIER_TABLE_NAME}.id"), nullable=False)
    carrier: Mapped["Carrier"] = relationship("Carrier")

    status: Mapped[str] = mapped_column(String, nullable=False)
    n_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tracking_number: Mapped[str] = mapped_column(String, nullable=False)
    tracking_link: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)

    manufacturer_creation_timestamp: Mapped[datetime] = mapped_column(nullable=False)
    manufacturer_estimated_delivery_timestamp: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    manufacturer_confirmed_delivery_timestamp: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    carrier_creation_timestamp: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    carrier_estimated_delivery_timestamp: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    carrier_confirmed_delivery_timestamp: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    SLS: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    SRS: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "manufacturer_order_id": self.manufacturer_order_id,
            "manufacturer_id": self.manufacturer_id,
            "site_id": self.site_id,
            "carrier_id": self.carrier_id,
            "status": self.status,
            "n_steps": self.n_steps,
            "tracking_number": self.tracking_number,
            "tracking_link": self.tracking_link,
            "manufacturer_creation_timestamp": self.manufacturer_creation_timestamp.isoformat(),
            "manufacturer_estimated_delivery_timestamp": self.manufacturer_estimated_delivery_timestamp.isoformat() if self.manufacturer_estimated_delivery_timestamp else None,
            "manufacturer_confirmed_delivery_timestamp": self.manufacturer_confirmed_delivery_timestamp.isoformat() if self.manufacturer_confirmed_delivery_timestamp else None,
            "carrier_creation_timestamp": self.carrier_creation_timestamp.isoformat() if self.carrier_creation_timestamp else None,
            "carrier_estimated_delivery_timestamp": self.carrier_estimated_delivery_timestamp.isoformat() if self.carrier_estimated_delivery_timestamp else None,
            "carrier_confirmed_delivery_timestamp": self.carrier_confirmed_delivery_timestamp.isoformat() if self.carrier_confirmed_delivery_timestamp else None,
            "SLS": self.SLS,
            "SRS": self.SRS,
        }

    def __str__(self) -> str:
        return (f"Order(id={self.id}, "
                f"manufacturer_order_id={self.manufacturer_order_id}, "
                f"manufacturer_id={self.manufacturer_id}, "
                f"site_id={self.site_id}, carrier_id={self.carrier_id}, "
                f"status={self.status}, n_steps={self.n_steps}, "
                f"tracking_number={self.tracking_number}, tracking_link={self.tracking_link}, "
                f"manufacturer_creation_timestamp={self.manufacturer_creation_timestamp}, "
                f"manufacturer_estimated_delivery_timestamp={self.manufacturer_estimated_delivery_timestamp}, "
                f"manufacturer_confirmed_delivery_timestamp={self.manufacturer_confirmed_delivery_timestamp}, "
                f"carrier_creation_timestamp={self.carrier_creation_timestamp}, "
                f"carrier_estimated_delivery_timestamp={self.carrier_estimated_delivery_timestamp}, "
                f"carrier_confirmed_delivery_timestamp={self.carrier_confirmed_delivery_timestamp}, "
                f"SLS={self.SLS})")