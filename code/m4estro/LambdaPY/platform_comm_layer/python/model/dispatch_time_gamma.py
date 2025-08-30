from typing import TYPE_CHECKING

from sqlalchemy import Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base
from model import site
if TYPE_CHECKING:
    from model.site import Site

DISPATCH_TIME_GAMMA_TABLE_NAME = 'dispatch_time_gammas'

class DispatchTimeGamma(Base):
    __tablename__ = DISPATCH_TIME_GAMMA_TABLE_NAME
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    site_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{site.SITE_TABLE_NAME}.id"))
    site: Mapped["Site"] = relationship("Site")
    
    shape: Mapped[float] = mapped_column(Float, nullable=False)
    loc: Mapped[float] = mapped_column(Float, nullable=False)
    scale: Mapped[float] = mapped_column(Float, nullable=False)
    skewness: Mapped[float] = mapped_column(Float, nullable=False)
    kurtosis: Mapped[float] = mapped_column(Float, nullable=False)
    mean: Mapped[float] = mapped_column(Float, nullable=False)
    std_dev: Mapped[float] = mapped_column(Float, nullable=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False)

    def __str__(self):
        return (f"DispatchTimeGamma(id={self.id}, site_id={self.site_id}, "
                f"shape={self.shape}, loc={self.loc}, scale={self.scale}, "
                f"skewness={self.skewness}, kurtosis={self.kurtosis}, "
                f"mean={self.mean}, std_dev={self.std_dev}, n={self.n})")