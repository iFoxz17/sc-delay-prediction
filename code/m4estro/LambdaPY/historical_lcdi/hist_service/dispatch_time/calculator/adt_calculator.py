from hist_service.dispatch_time.dto.dispatch_time_dist_dto import DispatchTimeDistDTO
from hist_service.dispatch_time.dto.dispatch_time_gamma_dto import DispatchTimeGammaDTO 
from hist_service.dispatch_time.dto.dispatch_time_sample_dto import DispatchTimeSampleDTO

from hist_service.dispatch_time.dto.adt_dto import ADT_DTO

from stats_utils import compute_gamma_mean

class ADTCalculator:
    def __init__(self) -> None:
        pass

    def adt(self, dto: DispatchTimeDistDTO) -> ADT_DTO:
        if isinstance(dto, DispatchTimeGammaDTO):
            return self.adt_gamma(dto)
        elif isinstance(dto, DispatchTimeSampleDTO):
            return self.adt_sample(dto)
        
        raise ValueError("Unknown distribution dto: {}".format(dto))

    def adt_gamma(self, dto: DispatchTimeGammaDTO) -> ADT_DTO:        
        mean: float = compute_gamma_mean(
            shape=dto.shape,
            scale=dto.scale,
            loc=dto.loc,
        )
        
        return ADT_DTO(value=mean)
    
    def adt_sample(self, dto: DispatchTimeSampleDTO) -> ADT_DTO:
        mean: float = dto.mean

        return ADT_DTO(value=mean)