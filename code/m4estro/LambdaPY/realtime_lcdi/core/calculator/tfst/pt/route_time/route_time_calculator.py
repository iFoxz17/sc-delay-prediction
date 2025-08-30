import numpy as np

from core.calculator.tfst.pt.route_time.route_time_estimator import RouteTimeEstimator

from core.calculator.tfst.pt.route_time.route_time_input_dto import RouteTimeInputDTO 
from core.calculator.tfst.pt.route_time.route_time_dto import RouteTimeDTO

from logger import get_logger
logger = get_logger(__name__)

class RouteTimeCalculator:
    def __init__(self, estimator: RouteTimeEstimator, mape: float) -> None:
        self.estimator: RouteTimeEstimator = estimator
        self.mape: float = mape

    def calculate(self, route_time_dto: RouteTimeInputDTO, confidence: float) -> RouteTimeDTO:
        mape: float = self.mape
        estimated_route_time_vec: np.ndarray = self.estimator.predict(route_time_dto)
        estimated_route_time: float = float(estimated_route_time_vec[0])
        
        route_time: RouteTimeDTO = RouteTimeDTO(
            lower=estimated_route_time * (1 - confidence * mape),
            upper=estimated_route_time * (1 + confidence * mape)
        )
        logger.debug(f"Calculated route time with mape={mape}: {route_time}")
        return route_time