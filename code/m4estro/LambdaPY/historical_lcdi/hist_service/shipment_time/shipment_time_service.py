from typing import Any, Set, List, Dict, Tuple
from collections import defaultdict

from sqlalchemy import tuple_, func

from service.read_only_db_connector import ReadOnlyDBConnector
from service.db_utils import get_read_only_db_connector

from model.site import Site
from model.carrier import Carrier
from model.shipment_time import ShipmentTime
from model.shipment_time_gamma import ShipmentTimeGamma
from model.shipment_time_sample import ShipmentTimeSample
from model.param import Param, ParamName

from utils.parsing import parse_id_list, parse_str_list

from hist_service.shipment_time.dto.shipment_time_dist_dto import ShipmentTimeDistDTO
from hist_service.shipment_time.dto.shipment_time_gamma_dto import ShipmentTimeGammaDTO
from hist_service.shipment_time.dto.shipment_time_sample_dto import ShipmentTimeSampleDTO

from hist_service.shipment_time.calculator.ast_calculator import ASTCalculator
from hist_service.shipment_time.calculator.ctdi_calculator import CTDICalculator

from historical_api.q_params import HistoricalQParamsKeys

from logger import get_logger
logger = get_logger(__name__)

def calculate_shipment_time(query_params: Dict[str, str]) -> List[Dict[str, Any]]:
    suppliers_str: str = query_params.get(HistoricalQParamsKeys.SUPPLIER.value, '')
    logger.debug(f"Supplier query parameter values: {suppliers_str}")
    
    sites_str: str = query_params.get(HistoricalQParamsKeys.SITE.value, '')
    logger.debug(f"Site query parameter value: {sites_str}")

    carriers_str: str = query_params.get(HistoricalQParamsKeys.CARRIER_NAME.value, '')
    logger.debug(f"Carrier query parameter value: {carriers_str}")

    supplier_ids: Set[int] = parse_id_list(suppliers_str)
    logger.debug(f"Parsed supplier IDs: {supplier_ids}")
    
    explicit_site_ids: Set[int] = parse_id_list(sites_str)
    logger.debug(f"Parsed explicit site IDs: {explicit_site_ids}")

    carrier_tokens: Set[str] = parse_str_list(carriers_str)
    logger.debug(f"Parsed carrier tokens: {carrier_tokens}")

    connector: ReadOnlyDBConnector = get_read_only_db_connector()
    try:
        with connector.session_scope() as session:
            site_ids: Set[int] = set()
            if supplier_ids:
                site_ids.update(id_ for (id_,) in session.query(Site.id).filter(Site.supplier_id.in_(supplier_ids)).all())
            logger.debug(f"Site IDs extracted from suppliers: {site_ids}")
            
            site_ids.update(explicit_site_ids)

            if not site_ids and not suppliers_str and not sites_str:                        # If no suppliers or sites specified, fetch all sites
                site_ids.update(id_ for (id_,) in session.query(Site.id).filter(Site.n_orders > 0).all())
                logger.debug(f"No specific sites or suppliers provided, retrieved all sites with at least one order: {site_ids}")
            if not site_ids:
                logger.debug("No sites found")
                return []

            carrier_ids: Set[int] = set()
            if not carriers_str:
                carrier_ids = {c_id for (c_id,) in session.query(Carrier.id).filter(Carrier.n_orders > 0).all()}
                logger.debug(f"No specific carriers provided, retrieved all carriers with at least one order: {carrier_ids}")
            else:
                carrier_ids: Set[int] = {
                    c_id
                    for (c_id,) in session.query(Carrier.id)
                    .filter(func.lower(Carrier.name).in_(carrier_tokens))
                    .all()
                }
                logger.debug(f"Carrier IDs extracted from names: {carrier_ids}")
            if not carrier_ids:
                logger.debug("No carriers found")
                return []

            gamma_results: List[ShipmentTimeGamma] = (
                session.query(ShipmentTimeGamma)
                .filter(ShipmentTimeGamma.site_id.in_(site_ids))
                .filter(ShipmentTimeGamma.carrier_id.in_(carrier_ids))
                .all()
            )
            logger.debug(f"Retrieved {len(gamma_results)} ShipmentTimeGamma records")

            sample_results: List[ShipmentTimeSample] = (
                session.query(ShipmentTimeSample)
                .filter(ShipmentTimeSample.site_id.in_(site_ids))
                .filter(ShipmentTimeSample.carrier_id.in_(carrier_ids))
                .all()
            )
            logger.debug(f"Retrieved {len(sample_results)} ShipmentTimeSample records")
            
            sample_x_by_pair: Dict[Tuple[int, int], List[float]] = defaultdict(list)
            if not sample_results:
                sample_x: List[Any] = []
                logger.debug("No ShipmentTimeSample records found for requested pairs, no ShipmentTime needed")
            else:
                sample_pairs: List[Tuple[int, int]] = [(s.site_id, s.carrier_id) for s in sample_results]
                sample_x = (
                    session.query(ShipmentTime.site_id, ShipmentTime.carrier_id, ShipmentTime.hours)
                    .filter(tuple_(ShipmentTime.site_id, ShipmentTime.carrier_id).in_(sample_pairs))
                    .all()
                )

                for s_id, c_id, hours in sample_x:
                    sample_x_by_pair[(s_id, c_id)].append(hours)
                logger.debug(f"Grouped {len(sample_x_by_pair)} ShipmentTime records by site and carrier")

                if len(sample_x_by_pair) != len(sample_results):
                    logger.error(
                        "Mismatch between sample_x_by_pair (%d) and sample_results (%d). Check data integrity.",
                        len(sample_x_by_pair), len(sample_results)
                    )

            dtos: List[ShipmentTimeDistDTO] = []
            for g in gamma_results:
                dtos.append(ShipmentTimeGammaDTO.from_orm_model(g))
            for s in sample_results:
                raw_hours = sample_x_by_pair.get((s.site_id, s.carrier_id), [])
                dtos.append(ShipmentTimeSampleDTO.from_orm_model(raw_hours, s))

            confidence_level: float = session.query(Param.value).filter(Param.name == ParamName.SHIPMENT_HIST_CONFIDENCE.value).scalar()
            logger.debug(f"Confidence level: {confidence_level}")

    except Exception:
        logger.exception("Exception during database query")
        raise

    ast_calc: ASTCalculator = ASTCalculator()
    ctdi_calc: CTDICalculator = CTDICalculator(confidence_level=confidence_level)
    st_indicators: List[Dict[str, Any]] = []
    for dto in dtos:
        ast_dto = ast_calc.ast(dto)
        ctdi_dto = ctdi_calc.ctdi(dto)
        st_indicators.append({
            "site": {
                "id": dto.site_id,
                "location": dto.site_location,
            },
            "supplier": {
                "id": dto.supplier_id,
                "manufacturer_id": dto.manufacturer_supplier_id,
                "name": dto.supplier_name,
            },
            "carrier": {
                "id": dto.carrier_id,
                "name": dto.carrier_name,
            },
            "indicators": {
                "AST": ast_dto.value, 
                "CTDI": {"lower": ctdi_dto.lower, "upper": ctdi_dto.upper, "confidence": confidence_level}
                }
        })

    return st_indicators