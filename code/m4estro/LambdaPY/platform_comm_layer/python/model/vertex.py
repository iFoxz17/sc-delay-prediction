from enum import Enum
from typing import Any, Optional, Set
from sqlalchemy import String, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base

class VertexType(Enum):
    SUPPLIER_SITE = 'SUPPLIER_SITE'
    INTERMEDIATE = 'INTERMEDIATE'
    MANUFACTURER = 'MANUFACTURER'

    @classmethod
    def _missing_(cls: type["VertexType"], value: Any) -> Optional["VertexType"]:
        if isinstance(value, str):
            normalized = value.strip().upper()

            for member in cls:
                if member.value == normalized:
                    return member

            if normalized in {"SUPPLIER", "SITE", "SUPPLIERSITE"}:
                return cls.SUPPLIER_SITE

        return None
    
    @classmethod
    def get_all_types(cls) -> Set["VertexType"]:
        return set([member for member in cls])

VERTEX_TABLE_NAME = 'vertices'

class Vertex(Base):
    __tablename__ = VERTEX_TABLE_NAME
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[VertexType] = mapped_column(
        SQLEnum(VertexType, name="vertex_type", native_enum=False),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint('name', 'type', name='uq_vertex_name_type'),
    )

    def __str__(self) -> str:
        return f"Vertex(id={self.id}, name={self.name}, type={self.type})"
