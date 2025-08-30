from datetime import date as dt_date
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum

from model.base import Base
from model import country
if TYPE_CHECKING:
    from model.country import Country

class HolidayCategory(Enum):
    WORKING = 'WORKING'
    CLOSURE = 'CLOSURE'

HOLIDAYS_TABLE_NAME = 'holidays'

class Holiday(Base):
    __tablename__ = HOLIDAYS_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    
    country_code: Mapped[str] = mapped_column(String, ForeignKey(f'{country.COUNTRY_TABLE_NAME}.code'))
    country: Mapped["Country"] = relationship("Country")
    
    category: Mapped[HolidayCategory] = mapped_column(
        SQLEnum(HolidayCategory, name="holiday_category", native_enum=False),
        nullable=False
    )

    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date: Mapped[datetime] = mapped_column(nullable=False)
    week_day: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year_day: Mapped[int] = mapped_column(Integer, nullable=False)

    def __str__(self) -> str:
        return (f"Holiday(id={self.id}, name={self.name}, country_code={self.country_code}, "
                f"category={self.category}, description={self.description}, url={self.url}, "
                f"type={self.type}, date={self.date}, week_day={self.week_day}, "
                f"month={self.month}, year_day={self.year_day})")
