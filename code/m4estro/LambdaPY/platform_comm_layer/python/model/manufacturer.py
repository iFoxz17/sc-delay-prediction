from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import location
if TYPE_CHECKING:
    from model.location import Location

MANUFACTURER_TABLE_NAME = 'manufacturers'

class Manufacturer(Base):
    __tablename__ = MANUFACTURER_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    location_name: Mapped[str] = mapped_column(
        String, 
        ForeignKey(f"{location.LOCATION_TABLE_NAME}.name"), 
        nullable=False
    )
    
    location: Mapped["Location"] = relationship(
        "Location",
        primaryjoin="Manufacturer.location_name == Location.name",
        foreign_keys=[location_name],
        uselist=False
    )
    
    def __str__(self) -> str:
        return (f"Manufacturer(id={self.id}, name={self.name} location_name={self.location_name})")