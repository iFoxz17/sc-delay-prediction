from typing import Set
from enum import Enum

class OrdersQParamsKeys(Enum):
    STATUS = "status" 
    BY = "by"

class VerticesQParamsKeys(Enum):
    NAME = "name"
    TYPE = "type"

    @classmethod
    def get_all_keys(cls) -> Set[str]:
        return {member.value for member in cls}
    
class By(Enum):
    ID = "id"
    MANUFACTURER_ID = "manufacturer_id"