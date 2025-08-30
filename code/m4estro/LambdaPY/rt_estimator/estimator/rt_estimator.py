import logging
import numpy as np
from xgboost import Booster, DMatrix

from estimator.rt_estimator_input_dto import RTEstimatorBatchInputDTO
from estimator.rt_estimator_output_dto import RTEstimatorOutputDTO, RTEstimatorBatchOutputDTO

logger = logging.getLogger(__name__)

class RTEstimator:
    def __init__(self, model: Booster) -> None:
        self.model: Booster = model

    def predict(self, rt_estimator_batch_input: RTEstimatorBatchInputDTO) -> RTEstimatorBatchOutputDTO:
        model: Booster = self.model   
            
        input_array: np.ndarray = np.array([
            [
                dto.distance,
                dto.avg_tmi, dto.tmi,
                dto.avg_wmi, dto.wmi,
                dto.avg_oti
            ] for dto in rt_estimator_batch_input.batch
        ])
        dmatrix: DMatrix = DMatrix(input_array)
        predictions: np.ndarray = model.predict(dmatrix)
        logger.debug(f"Computed {len(predictions)} predictions using the model.")

        return RTEstimatorBatchOutputDTO(batch=[RTEstimatorOutputDTO(time=pred) for pred in predictions])