from typing import List, Union, Optional

import numpy as np

from core.calculator.tfst.pt.route_time.route_time_input_dto import RouteTimeInputDTO
from core.calculator.tfst.pt.route_time.rt_estimator_lambda_client import (
    RTEstimatorLambdaClient, 
    RTEstimationRequest, RTEstimationBatchRequest, 
    RTEstimatorResponse, RTEstimatorBatchResponse
)

from logger import get_logger
logger = get_logger(__name__)

class RouteTimeEstimator:
    def __init__(self, rt_estimator_client: RTEstimatorLambdaClient, use_model: bool = True) -> None:
        self.rt_estimator_client: RTEstimatorLambdaClient = rt_estimator_client
        self.use_model: bool = use_model

    def predict(self, route_time_dto: Union[RouteTimeInputDTO, List[RouteTimeInputDTO]]) -> np.ndarray:
        dtos: List[RouteTimeInputDTO] = route_time_dto if isinstance(route_time_dto, List) else [route_time_dto]
        
        if not self.use_model:
            logger.debug("Model usage is disabled. Returning average OTI for all route times.")
            return np.array([dto.avg_oti for dto in dtos])

        client: RTEstimatorLambdaClient = self.rt_estimator_client
        
        predictions: List[float] = []
        batch_data: List[RTEstimationRequest] = []
        batch_indices: List[int] = []
        
        for i, dto in enumerate(dtos):
            if not dto.tmi.computed or not dto.wmi.computed:
                predictions.append(dto.avg_oti)
                logger.debug(f"Skipping prediction for index {i} due to missing TMI or WMI: defaulting to avg_oti={dto.avg_oti}")
            else:
                batch_data.append(RTEstimationRequest.from_route_time_input_dto(dto))
                batch_indices.append(i)
                predictions.append(0.0)  # Placeholder
                logger.debug(f"Input data for index {i} added to batch for prediction.")

        if batch_data:
            batch_request: RTEstimationBatchRequest = RTEstimationBatchRequest(batch=batch_data)
            batch_response: Optional[RTEstimatorBatchResponse] = client.get_rt_estimation(batch_request)
            if batch_response is None:
                logger.warning("Received empty response from RT estimator client. Defaulting predictions to avg_oti.")
                batch_response = RTEstimatorBatchResponse(batch=[RTEstimatorResponse(time=rt_est_request.avg_oti) for rt_est_request in batch_data])

            for idx, pred in zip(batch_indices, batch_response.batch):
                predictions[idx] = pred.time

        logger.debug(f"Predictions: {predictions}")

        return np.array(predictions)