from typing import Tuple
from numbers import Number

from hist_service.dispatch_time.dto.dispatch_time_dist_dto import DispatchTimeDistDTO
from hist_service.dispatch_time.dto.dispatch_time_gamma_dto import DispatchTimeGammaDTO 
from hist_service.dispatch_time.dto.dispatch_time_sample_dto import DispatchTimeSampleDTO

from hist_service.dispatch_time.dto.ddi_dto import DDI_DTO

from stats_utils import compute_gamma_mean, compute_gamma_ci, compute_sample_ci

class DDICalculator:
    def __init__(self, confidence_level: float) -> None:
        assert isinstance(confidence_level, Number) and 0 < confidence_level < 1

        self.confidence_level: float = confidence_level

    def ddi(self, dto: DispatchTimeDistDTO) -> DDI_DTO:
        if isinstance(dto, DispatchTimeGammaDTO):
            return self.ddi_gamma(dto)
        elif isinstance(dto, DispatchTimeSampleDTO):
            return self.ddi_sample(dto)
        
        raise ValueError("Unknown distribution dto: {}".format(dto))

    def ddi_gamma(self, dto: DispatchTimeGammaDTO) -> DDI_DTO:

        mean: float = compute_gamma_mean(shape=dto.shape, scale=dto.scale, loc=dto.loc)
        ci: Tuple[float, float] = compute_gamma_ci(shape=dto.shape, scale=dto.scale, loc=dto.loc, confidence_level=self.confidence_level)
        l: float = ci[0]
        u: float = ci[1]

        return DDI_DTO(lower=mean - l, upper=u - mean)
    
    def ddi_sample(self, dto: DispatchTimeSampleDTO) -> DDI_DTO:

        mean: float = dto.mean
        ci: Tuple[float, float] = compute_sample_ci(x=dto.x, confidence_level=self.confidence_level)
        l: float = ci[0]
        u: float = ci[1]

        return DDI_DTO(lower=mean - l, upper=u - mean)