from typing import Optional, TYPE_CHECKING
from sqlalchemy import Float, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import country
if TYPE_CHECKING:
    from model.country import Country

LOCATION_TABLE_NAME = 'locations'

class Location(Base):
    __tablename__ = LOCATION_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    
    city: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    country_code: Mapped[str] = mapped_column(
        String, 
        ForeignKey(f'{country.COUNTRY_TABLE_NAME}.code'), 
        nullable=False
    )
    country: Mapped["Country"] = relationship("Country")
    
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    def __str__(self) -> str:
        return (f"Location(id={self.id}, name={self.name}, city={self.city}, "
                f"state={self.state}, country_code={self.country_code}, "
                f"latitude={self.latitude}, longitude={self.longitude})")