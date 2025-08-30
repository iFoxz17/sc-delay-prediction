from hist_service.dri.dri_dto import DRI_DTO

class DRICalculator:
    def __init__(self):
        pass

    def calculate_dri(self, n_rejections: float, n_orders: float) -> DRI_DTO:
        if n_orders == 0:
            return DRI_DTO(value=0.0)
        
        dri: float = n_rejections / n_orders
        return DRI_DTO(value=dri)