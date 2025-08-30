from dataclasses import dataclass

from hist_service.shipment_time.dto.shipment_time_dist_dto import ShipmentTimeDistDTO

from model.shipment_time_gamma import ShipmentTimeGamma

@dataclass(frozen=True)
class ShipmentTimeGammaDTO(ShipmentTimeDistDTO):
    shape: float
    loc: float
    scale: float
    skewness: float
    kurtosis: float

    @classmethod
    def from_orm_model(cls, orm: ShipmentTimeGamma) -> "ShipmentTimeGammaDTO":
        return cls(
            site_id=orm.site_id,
            site_location=orm.site.location_name,
            supplier_id=orm.site.supplier_id,
            manufacturer_supplier_id=orm.site.supplier.manufacturer_supplier_id,
            supplier_name=orm.site.supplier.name,
            carrier_id=orm.carrier_id,
            carrier_name=orm.carrier.name,
            mean=orm.mean,
            std_dev=orm.std_dev,
            n=orm.n,
            shape=orm.shape,
            loc=orm.loc,
            scale=orm.scale,
            skewness=orm.skewness,
            kurtosis=orm.kurtosis,
        )