from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import supplier, location
if TYPE_CHECKING:
    from model.supplier import Supplier
    from model.location import Location

SITE_TABLE_NAME = 'sites'

class Site(Base):
    __tablename__ = SITE_TABLE_NAME

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{supplier.SUPPLIER_TABLE_NAME}.id"), nullable=False)
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="sites")

    location_name: Mapped[str] = mapped_column(String, ForeignKey(f"{location.LOCATION_TABLE_NAME}.name"), nullable=False)
    location: Mapped["Location"] = relationship(
        "Location",
        primaryjoin="Site.location_name == Location.name",
        foreign_keys=[location_name],
        uselist=False
    )

    n_rejections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    consider_closure_holidays: Mapped[bool] = mapped_column(Integer, nullable=False, default=True, comment='Whether to consider closure holidays for this site')
    consider_weekends_holidays: Mapped[bool] = mapped_column(Integer, nullable=False, default=True, comment='Whether to consider weekends as closure for this site')
    consider_working_holidays: Mapped[bool] = mapped_column(Integer, nullable=False, default=True, comment='Whether to consider working holidays on weekends for this site')

    __table_args__ = (
        UniqueConstraint('supplier_id', 'location_name', name='uq_supplier_location'),
    )

    def __str__(self) -> str:
        return (f"Site(id={self.id}, supplier_id={self.supplier_id}, "
                f"location_name={self.location_name}, n_rejections={self.n_rejections}, "
                f"n_orders={self.n_orders})")
