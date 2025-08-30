from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base

CARRIER_TABLE_NAME = 'carriers'

class Carrier(Base):
    __tablename__ = CARRIER_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    carrier_17track_id: Mapped[Optional[str]] = mapped_column(nullable=True, unique=True)

    n_losses: Mapped[int] = mapped_column(nullable=False, default=0)
    n_orders: Mapped[int] = mapped_column(nullable=False, default=0)
    
    def __str__(self) -> str:
        return (f"Carrier(id={self.id}, name={self.name}, carrier_17track_id={self.carrier_17track_id}, "
                f"n_losses={self.n_losses}, n_orders={self.n_orders})")