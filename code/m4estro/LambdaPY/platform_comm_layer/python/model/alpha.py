from typing import Optional
from enum import Enum

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column 

from model.base import Base

class AlphaType(Enum):
    CONST = 'CONST'
    EXP = 'EXP'
    MARKOV = 'MARKOV'

    @classmethod
    def as_code(cls, alpha_type: 'AlphaType') -> int:
        match alpha_type:
            case cls.CONST:
                return 0
            case cls.EXP:
                return 1
            case cls.MARKOV:
                return 2
            
        raise ValueError(f"No Alpha enum with type: {alpha_type}")

    @classmethod
    def from_code(cls, code: int) -> 'AlphaType':
        match code:
            case 0:
                return cls.CONST
            case 1:
                return cls.EXP
            case 2:
                return cls.MARKOV
        raise ValueError(f"No Alpha enum with code: {code}")
    
ALPHA_TABLE_NAME: str = "alphas"

class Alpha(Base):
    __tablename__ = ALPHA_TABLE_NAME
    
    id: Mapped[int]= mapped_column(primary_key=True)
    type: Mapped[AlphaType] = mapped_column(
        SQLEnum(AlphaType, name="type", native_enum=False),
        nullable=False
    )

    tt_weight: Mapped[Optional[float]] = mapped_column(nullable=True)
    tau: Mapped[Optional[float]] = mapped_column(nullable=True)
    gamma: Mapped[Optional[float]] = mapped_column(nullable=True)

    input: Mapped[float] = mapped_column(nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)

    def __str__(self) -> str:
        return (f"Alpha(id={self.id}, type={self.type}, "
                f"tt_weight={self.tt_weight}, tau={self.tau}, "
                f"gamma={self.gamma}, input={self.input}, value={self.value})")