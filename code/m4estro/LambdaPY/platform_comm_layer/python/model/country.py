from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base

COUNTRY_TABLE_NAME = 'countries'

class Country(Base):
    __tablename__ = COUNTRY_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(nullable=False, unique=True)
    name: Mapped[str] = mapped_column(nullable=False)
    total_holidays: Mapped[int] = mapped_column(nullable=False)
    weekend_start: Mapped[int] = mapped_column(nullable=False, default=6)
    weekend_end: Mapped[int] = mapped_column(nullable=False, default=7)
    
    def __str__(self) -> str:
        return (f"Country(id={self.id}, code={self.code}, name={self.name}, "
                f"total_holidays={self.total_holidays}, weekend_start={self.weekend_start}, "
                f"weekend_end={self.weekend_end})")