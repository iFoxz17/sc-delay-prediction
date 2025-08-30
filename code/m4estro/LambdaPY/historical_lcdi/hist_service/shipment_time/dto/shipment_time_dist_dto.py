from abc import ABC
from dataclasses import dataclass

@dataclass(frozen=True)
class ShipmentTimeDistDTO(ABC):
    site_id: int
    site_location: str
    supplier_id: int
    manufacturer_supplier_id: int
    supplier_name: str
    carrier_id: int
    carrier_name: str
    mean: float
    std_dev: float
    n: int