from dataclasses import dataclass

from hist_service.shipment_time.dto.shipment_time_dist_dto import ShipmentTimeDistDTO

from model.shipment_time_sample import ShipmentTimeSample

@dataclass(frozen=True)
class ShipmentTimeSampleDTO(ShipmentTimeDistDTO):
    x: list[float]
    median: float

    @classmethod
    def from_orm_model(cls, x:list[float], orm: ShipmentTimeSample) -> "ShipmentTimeSampleDTO":
        return cls(
            x=x,
            site_id=orm.site_id,
            site_location=orm.site.location_name,
            supplier_id=orm.site.supplier_id,
            supplier_name=orm.site.supplier.name,
            manufacturer_supplier_id=orm.site.supplier.manufacturer_supplier_id,
            carrier_id=orm.carrier_id,
            carrier_name=orm.carrier.name,
            mean=orm.mean,
            std_dev=orm.std_dev,
            n=orm.n,
            median=orm.median
        )