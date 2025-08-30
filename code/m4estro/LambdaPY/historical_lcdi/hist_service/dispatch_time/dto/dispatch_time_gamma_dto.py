from dataclasses import dataclass

from model.dispatch_time_gamma import DispatchTimeGamma

from hist_service.dispatch_time.dto.dispatch_time_dist_dto import DispatchTimeDistDTO

@dataclass(frozen=True)
class DispatchTimeGammaDTO(DispatchTimeDistDTO):
    shape: float
    loc: float
    scale: float
    skewness: float
    kurtosis: float

    @classmethod
    def from_orm_model(cls, orm: DispatchTimeGamma) -> "DispatchTimeGammaDTO":
        return cls(
            site_id=orm.site_id,
            site_location=orm.site.location_name,
            supplier_id=orm.site.supplier_id,
            manufacturer_supplier_id=orm.site.supplier.manufacturer_supplier_id,
            supplier_name=orm.site.supplier.name,
            mean=orm.mean,
            std_dev=orm.std_dev,
            n=orm.n,
            shape=orm.shape,
            loc=orm.loc,
            scale=orm.scale,
            skewness=orm.skewness,
            kurtosis=orm.kurtosis,
        )