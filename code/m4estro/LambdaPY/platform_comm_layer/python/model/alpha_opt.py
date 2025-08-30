from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column

from model.base import Base
from model import site, carrier
if TYPE_CHECKING:
    from model.site import Site
    from model.carrier import Carrier

ALPHA_OPT_TABLE_NAME = 'alphas_opt'

class AlphaOpt(Base):
    __tablename__ = ALPHA_OPT_TABLE_NAME
    id: Mapped[int] = mapped_column(primary_key=True)

    site_id: Mapped[int] = mapped_column(ForeignKey(f"{site.SITE_TABLE_NAME}.id"), nullable=False)
    site: Mapped["Site"] = relationship("Site")

    carrier_id: Mapped[int] = mapped_column(ForeignKey(f"{carrier.CARRIER_TABLE_NAME}.id"), nullable=False)
    carrier: Mapped["Carrier"] = relationship("Carrier")

    tt_weight: Mapped[float] = mapped_column(nullable=False, default=0.5)

    __table_args__ = (
        UniqueConstraint('site_id', 'carrier_id', name='uq_alpha_opt_site_carrier'),
    )

    def __str__(self) -> str:
        return f"AlphaOpt(site_id={self.site_id}, carrier_id={self.carrier_id}, tt_weight={self.tt_weight})"