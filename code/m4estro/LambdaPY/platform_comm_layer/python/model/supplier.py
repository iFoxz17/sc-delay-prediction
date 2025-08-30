from typing import List, TYPE_CHECKING
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
if TYPE_CHECKING:
    from model.site import Site

SUPPLIER_TABLE_NAME = 'suppliers'

class Supplier(Base):
    __tablename__ = SUPPLIER_TABLE_NAME

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer_supplier_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    sites: Mapped[List["Site"]] = relationship("Site", back_populates="supplier", cascade="all, delete-orphan")

    def __str__(self) -> str:
        return f"Supplier(id={self.id}, manufacturer_supplier_id={self.manufacturer_supplier_id}, name='{self.name}')"
