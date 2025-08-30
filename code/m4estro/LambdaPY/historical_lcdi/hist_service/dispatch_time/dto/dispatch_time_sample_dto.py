from dataclasses import dataclass

from model.dispatch_time_sample import DispatchTimeSample

from hist_service.dispatch_time.dto.dispatch_time_dist_dto import DispatchTimeDistDTO

@dataclass(frozen=True)
class DispatchTimeSampleDTO(DispatchTimeDistDTO):
    x: list[float]
    median: float

    @classmethod
    def from_orm_model(cls, x:list[float], orm: DispatchTimeSample) -> "DispatchTimeSampleDTO":
        return cls(
            x=x,
            site_id=orm.site_id,
            site_location=orm.site.location_name,
            supplier_id=orm.site.supplier_id,
            manufacturer_supplier_id=orm.site.supplier.manufacturer_supplier_id,
            supplier_name=orm.site.supplier.name,
            mean=orm.mean,
            std_dev=orm.std_dev,
            n=orm.n,
            median=orm.median
        )