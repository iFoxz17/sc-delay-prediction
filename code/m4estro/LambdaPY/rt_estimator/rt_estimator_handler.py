import json
import logging
from typing import Any, Dict

from pydantic import TypeAdapter, ValidationError

from estimator.rt_estimator import RTEstimator
from estimator.rt_estimator_input_dto import RTEstimatorInputDTO, RTEstimatorBatchInputDTO
from estimator.rt_estimator_output_dto import RTEstimatorBatchOutputDTO
from estimator.rt_serializer import S3RTEstimatorSerializer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def _parse_input(data: Any) -> RTEstimatorBatchInputDTO:
    try:
        return TypeAdapter(RTEstimatorBatchInputDTO).validate_python(data)
    except ValidationError:
        logger.warning("Failed to parse input as batch, retrying as single DTO.")
        try:
            single_dto = TypeAdapter(RTEstimatorInputDTO).validate_python(data)
            return RTEstimatorBatchInputDTO(batch=[single_dto])
        except ValidationError as e:
            logger.error("Failed to parse input as single DTO", exc_info=e)
            raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.debug(f"Received event: {json.dumps(event)}")

    try:
        batch_input: RTEstimatorBatchInputDTO = _parse_input(event)
    except Exception:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid input data"})
        }
    logger.debug(f"Parsed input DTO: {batch_input}")

    try:
        estimator: RTEstimator = S3RTEstimatorSerializer().deserialize()
        logger.debug("Route time estimator model loaded successfully")
    except Exception as e:
        logger.error("Failed to deserialize route time estimator", exc_info=e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to load model"})
        }

    try:
        batch_predictions: RTEstimatorBatchOutputDTO = estimator.predict(batch_input)
        logger.debug(f"Predictions: {batch_predictions}")
    except Exception as e:
        logger.error("Prediction failed", exc_info=e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Prediction failed"})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "input": batch_input.model_dump(),
            "predictions": batch_predictions.model_dump(),
        })
    }
