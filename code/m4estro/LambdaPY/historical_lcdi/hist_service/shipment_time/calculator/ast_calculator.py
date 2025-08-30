from hist_service.shipment_time.dto.shipment_time_dist_dto import ShipmentTimeDistDTO
from hist_service.shipment_time.dto.shipment_time_gamma_dto import ShipmentTimeGammaDTO 
from hist_service.shipment_time.dto.shipment_time_sample_dto import ShipmentTimeSampleDTO

from hist_service.shipment_time.dto.ast_dto import AST_DTO

from stats_utils import compute_gamma_mean

class ASTCalculator:
    def __init__(self) -> None:
        pass

    def ast(self, dto: ShipmentTimeDistDTO) -> AST_DTO:
        if isinstance(dto, ShipmentTimeGammaDTO):
            return self.ast_gamma(dto)
        elif isinstance(dto, ShipmentTimeSampleDTO):
            return self.ast_sample(dto)
        
        raise ValueError("Unknown distribution dto: {}".format(dto))

    def ast_gamma(self, dto: ShipmentTimeGammaDTO) -> AST_DTO:        
        mean: float = compute_gamma_mean(
            shape=dto.shape,
            scale=dto.scale,
            loc=dto.loc,
        )
        
        return AST_DTO(value=mean)
    
    def ast_sample(self, dto: ShipmentTimeSampleDTO) -> AST_DTO:
        mean: float = dto.mean

        return AST_DTO(value=mean)