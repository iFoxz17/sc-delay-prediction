from typing import Dict, Any, List
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.api_gateway import Response

from concurrent.futures import ThreadPoolExecutor, Future

from hist_service.historical_lcdi_aggregator import HistoricalLCDIAggregator
from hist_service.dispatch_time.dispatch_time_service import calculate_dispatch_time
from hist_service.shipment_time.shipment_time_service import calculate_shipment_time
from hist_service.dri.dri_service import calculate_dri
from hist_service.cli.cli_service import calculate_cli

from utils.parsing import get_query_params
from utils.response import internal_error_response, success_response

from historical_api.q_params import HistoricalQParamsKeys

from logger import get_logger
logger = get_logger(__name__)

SHIPMENT_FUTURE_KEY = "shipment"
DISPATCH_FUTURE_KEY = "dispatch"
DRI_FUTURE_KEY = "dri"
CLI_FUTURE_KEY = "cli"

HISTORICAL_BASE_PATH = "/lcdi/historical"

app = APIGatewayRestResolver()

@app.get(HISTORICAL_BASE_PATH)
def get_historical_lcdi() -> Response:
    q_params: Dict[str, str] = get_query_params(
        app.current_event.query_string_parameters,
        allowed_keys={key.value for key in HistoricalQParamsKeys}
    )
    logger.debug(f"Filtered query parameters for {HISTORICAL_BASE_PATH}: {q_params}")

    with ThreadPoolExecutor() as executor:
        futures: Dict[str, Future[List[Dict[str, Any]]]] = {
            SHIPMENT_FUTURE_KEY: executor.submit(calculate_shipment_time, q_params),
            DISPATCH_FUTURE_KEY: executor.submit(calculate_dispatch_time, q_params),
            DRI_FUTURE_KEY: executor.submit(calculate_dri, q_params),
            CLI_FUTURE_KEY: executor.submit(calculate_cli, q_params)
        }

        try:
            dispatch_time_indicators: List[Dict[str, Any]] = futures[DISPATCH_FUTURE_KEY].result()
            logger.debug(f"Dispatch time indicators: {dispatch_time_indicators}")

            shipment_time_indicators: List[Dict[str, Any]] = futures[SHIPMENT_FUTURE_KEY].result()
            logger.debug(f"Shipment time indicators: {shipment_time_indicators}")
            
            dri_indicators: List[Dict[str, Any]] = futures[DRI_FUTURE_KEY].result()
            logger.debug(f"DRI indicators: {dri_indicators}")

            cli_indicators: List[Dict[str, Any]] = futures[CLI_FUTURE_KEY].result()
            logger.debug(f"CLI indicators: {cli_indicators}")
        except Exception as e:
            logger.exception("Error during historical LCDI calculations")
            return internal_error_response(f"Error during calculations: {str(e)}")
        
    aggregator = HistoricalLCDIAggregator(
        dispatch_time_indicators=dispatch_time_indicators,
        shipment_time_indicators=shipment_time_indicators,
        dri_indicators=dri_indicators,
        cli_indicators=cli_indicators
    )

    aggregated_indicators = aggregator.aggregate()
    logger.debug(f"Aggregated indicators: {aggregated_indicators}")

    return success_response(aggregated_indicators)


@app.get(f"{HISTORICAL_BASE_PATH}/cli")
def get_cli() -> Response:
    q_params: Dict[str, str] = get_query_params(
        app.current_event.query_string_parameters,
        allowed_keys={HistoricalQParamsKeys.CARRIER_NAME.value}
    )
    logger.debug(f"Filtered query parameters for {HISTORICAL_BASE_PATH}/cli: {q_params}")

    cli_indicators: List[Dict[str, Any]] = calculate_cli(q_params)
    logger.debug(f"CLI indicators: {cli_indicators}")
    return success_response(cli_indicators)
    
@app.get(f"{HISTORICAL_BASE_PATH}/shipment-time")
def get_shipment_time() -> Response:
    q_params: Dict[str, str] = get_query_params(
        app.current_event.query_string_parameters,
        allowed_keys={key.value for key in HistoricalQParamsKeys}
    )
    logger.debug(f"Filtered query parameters for {HISTORICAL_BASE_PATH}/shipment_time: {q_params}")

    shipment_time_indicators: List[Dict[str, Any]] = calculate_shipment_time(q_params)
    logger.debug(f"Shipment time indicators: {shipment_time_indicators}")
    return success_response(shipment_time_indicators)
    

@app.get(f"{HISTORICAL_BASE_PATH}/dispatch-time")
def get_dispatch_time() -> Response:
    q_params: Dict[str, str] = get_query_params(
        app.current_event.query_string_parameters,
        allowed_keys={HistoricalQParamsKeys.SITE.value, HistoricalQParamsKeys.SUPPLIER.value}
    )
    logger.debug(f"Filtered query parameters for {HISTORICAL_BASE_PATH}/dispatch-time: {q_params}")

    dispatch_time_indicators: list[Dict[str, Any]] = calculate_dispatch_time(q_params)
    logger.debug(f"Dispatch time indicators: {dispatch_time_indicators}")
    return success_response(dispatch_time_indicators)


@app.get(f"{HISTORICAL_BASE_PATH}/dri")
def get_dri() -> Response:
    q_params: Dict[str, str] = get_query_params(
        app.current_event.query_string_parameters,
        allowed_keys={HistoricalQParamsKeys.SITE.value, HistoricalQParamsKeys.SUPPLIER.value}
    )
    logger.debug(f"Filtered query parameters for {HISTORICAL_BASE_PATH}/dri: {q_params}")

    dri_indicators: List[Dict[str, Any]] = calculate_dri(q_params)
    logger.debug(f"DRI indicators: {dri_indicators}")
    return success_response(dri_indicators)
    

@app.exception_handler(Exception)
def handle_exception(e: Exception) -> Response:
    logger.exception("Unexpected error during historical LCDI computation")
    return internal_error_response(f"Unexpected error: {str(e)}")

def handler(event: Dict, context: LambdaContext) -> Dict:
    return app.resolve(event, context)