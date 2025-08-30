from numbers import Number

from hist_service.shipment_time.dto.shipment_time_dist_dto import ShipmentTimeDistDTO
from hist_service.shipment_time.dto.shipment_time_gamma_dto import ShipmentTimeGammaDTO 
from hist_service.shipment_time.dto.shipment_time_sample_dto import ShipmentTimeSampleDTO

from hist_service.shipment_time.dto.ctdi_dto import CTDI_DTO

from stats_utils import compute_gamma_mean, compute_gamma_ci, compute_sample_ci

class CTDICalculator:
    def __init__(self, confidence_level: float) -> None:
        assert isinstance(confidence_level, Number) and 0 < confidence_level < 1
        self.confidence_level: float = confidence_level

    def ctdi(self, dto: ShipmentTimeDistDTO) -> CTDI_DTO:
        if isinstance(dto, ShipmentTimeGammaDTO):
            return self.ctdi_gamma(dto)
        elif isinstance(dto, ShipmentTimeSampleDTO):
            return self.ctdi_sample(dto)
        
        raise ValueError("Unknown distribution dto: {}".format(dto))

    def ctdi_gamma(self, dto: ShipmentTimeGammaDTO) -> CTDI_DTO:
        mean: float = compute_gamma_mean(shape=dto.shape, scale=dto.scale, loc=dto.loc)
        l: float
        u: float
        l, u = compute_gamma_ci(shape=dto.shape, scale=dto.scale, loc=dto.loc, confidence_level=self.confidence_level)

        return CTDI_DTO(lower=mean - l, upper=u - mean)
    
    def ctdi_sample(self, dto: ShipmentTimeSampleDTO) -> CTDI_DTO:
        mean: float = dto.mean
        l: float
        u: float
        l, u = compute_sample_ci(x=dto.x, confidence_level=self.confidence_level)

        return CTDI_DTO(lower=mean - l, upper=u - mean)