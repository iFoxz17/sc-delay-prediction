from typing import Set
from enum import Enum

class RealtimeQParamKeys(Enum):
    ORDER = "order"
    VERTEX = "vertex"
    CARRIER_NAME = "carrier_name"

    @classmethod
    def get_all_values(cls) -> Set[str]:
        return {key.value for key in cls}
    
class PathQParamKeys(Enum):
    SOURCE = "source"
    CARRIER_NAME = "carrier_name"
    BY = "by"

    @classmethod
    def get_all_values(cls) -> Set[str]:
        return {key.value for key in cls}