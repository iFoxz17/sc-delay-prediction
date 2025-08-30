from typing import Any, List, Dict, Set
from sqlalchemy import func

from service.read_only_db_connector import ReadOnlyDBConnector
from service.db_utils import get_read_only_db_connector

from model.carrier import Carrier

from hist_service.cli.cli_calculator import CLICalculator
from hist_service.cli.cli_dto import CLI_DTO

from utils.parsing import parse_str_list

from historical_api.q_params import HistoricalQParamsKeys

from logger import get_logger
logger = get_logger(__name__)

def calculate_cli(query_params: Dict[str, str]) -> List[Dict[str, Any]]:
    carriers_str: str = query_params.get(HistoricalQParamsKeys.CARRIER_NAME.value, '')
    logger.debug(f"Carriers query parameter values: {carriers_str}")

    carrier_tokens: Set[str] = parse_str_list(carriers_str, case='lower')
    logger.debug(f"Parsed carrier tokens: {carrier_tokens}")
    
    connector: ReadOnlyDBConnector = get_read_only_db_connector()
    try:
        with connector.session_scope() as session:
            carrier_results: List[Carrier] = []
            if not carriers_str:
                logger.debug(f"No specific carriers provided, retrieving all carriers with at least one order")
                carrier_results: List[Carrier] = session.query(Carrier).filter(Carrier.n_orders > 0).all()
            else:
                logger.debug(f"Retrieving carriers with names: {carrier_tokens}")
                carrier_results: List[Carrier] = (
                    session.query(Carrier)
                    .filter(func.lower(Carrier.name).in_(carrier_tokens))
                    .all()
                )

            cli_calculator: CLICalculator = CLICalculator()
            cli_indicators: List[Dict[str, Any]] = []
            
            for carrier in carrier_results:
                cli: CLI_DTO = cli_calculator.calculate_cli(n_losses=carrier.n_losses, n_orders=carrier.n_orders)

                cli_indicators.append({
                    "carrier": {
                        "id": carrier.id,
                        "name": carrier.name
                    },
                    "indicators": {
                        "CLI": cli.value
                        }
                    })
            logger.debug(f"Calculated CLI indicators for {len(cli_indicators)} carriers")
            
            return cli_indicators

    except Exception:
        logger.exception("Exception during database query")
        raise
