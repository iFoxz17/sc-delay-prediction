from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import site
if TYPE_CHECKING:
    from model.site import Site

DISPATCH_TIME_TABLE_NAME = 'dispatch_times'

class DispatchTime(Base):
    __tablename__ = DISPATCH_TIME_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    site_id: Mapped[int] = mapped_column(ForeignKey(f"{site.SITE_TABLE_NAME}.id"))
    site: Mapped["Site"] = relationship("Site")

    hours: Mapped[float] = mapped_column(Float, nullable=False)
    
    def __str__(self) -> str:
        return (f"DispatchTime(id={self.id}, site_id={self.site_id}, hours={self.hours})")