from typing import Any, Set, List, Dict
from collections import defaultdict

from service.read_only_db_connector import ReadOnlyDBConnector
from service.db_utils import get_read_only_db_connector

from model.site import Site
from model.dispatch_time import DispatchTime
from model.dispatch_time_gamma import DispatchTimeGamma
from model.dispatch_time_sample import DispatchTimeSample
from model.param import Param, ParamName

from utils.parsing import parse_id_list

from hist_service.dispatch_time.dto.dispatch_time_dist_dto import DispatchTimeDistDTO
from hist_service.dispatch_time.dto.dispatch_time_gamma_dto import DispatchTimeGammaDTO
from hist_service.dispatch_time.dto.dispatch_time_sample_dto import DispatchTimeSampleDTO
from hist_service.dispatch_time.dto.adt_dto import ADT_DTO
from hist_service.dispatch_time.dto.ddi_dto import DDI_DTO

from hist_service.dispatch_time.calculator.adt_calculator import ADTCalculator
from hist_service.dispatch_time.calculator.ddi_calculator import DDICalculator

from historical_api.q_params import HistoricalQParamsKeys

from logger import get_logger
logger = get_logger(__name__)

def calculate_dispatch_time(query_params: dict[str, str]) -> list[Dict[str, Any]]:
    suppliers_str: str = query_params.get(HistoricalQParamsKeys.SUPPLIER.value, '')
    logger.debug(f"Supplier query parameter values: {suppliers_str}")

    sites_str: str = query_params.get(HistoricalQParamsKeys.SITE.value, '')
    logger.debug(f"Site query parameter value: {sites_str}")

    supplier_ids: Set[int] = parse_id_list(suppliers_str)
    logger.debug(f"Parsed supplier IDs: {supplier_ids}")

    connector: ReadOnlyDBConnector = get_read_only_db_connector()
    try:
        with connector.session_scope() as session:
            site_ids: Set[int] = set()

            if supplier_ids:
                site_ids.update(id_ for (id_,) in session.query(Site.id).filter(Site.supplier_id.in_(supplier_ids)).all())
            logger.debug(f"Site IDs extracted from suppliers: {site_ids}")

            site_ids.update(parse_id_list(sites_str))
            logger.debug(f"Site IDs after adding explicit sites: {site_ids}")

            if not site_ids and not suppliers_str and not sites_str:                # If no suppliers or sites specified, fetch all sites
                site_ids.update(id_ for (id_,) in session.query(Site.id).filter(Site.n_orders > 0).all())
                logger.debug(f"No specific sites or suppliers provided, retrieved all sites with at least one order: {site_ids}")

            gamma_results: List[DispatchTimeGamma] = session.query(DispatchTimeGamma).filter(DispatchTimeGamma.site_id.in_(site_ids)).all()
            logger.debug(f"Retrieved {len(gamma_results)} DispatchTimeGamma records")

            gamma_ids: Set[int] = {g.site_id for g in gamma_results}
            sample_ids: Set[int] = site_ids - gamma_ids

            sample_results: List[DispatchTimeSample] = session.query(DispatchTimeSample).filter(
                DispatchTimeSample.site_id.in_(sample_ids)
            ).order_by(DispatchTimeSample.site_id).all()
            
            logger.debug(f"Retrieved {len(gamma_results)} DispatchTimeSample records")

            sample_x: List[Any] = session.query(DispatchTime.site_id, DispatchTime.hours).filter(
                DispatchTime.site_id.in_(sample_ids)
            ).all()

            logger.debug(f"Retrieved {len(sample_x)} DispatchTime records")

            sample_x_by_site: Dict[int, List[float]] = defaultdict(list)
            for sid, hours in sample_x:
                sample_x_by_site[sid].append(hours)
            logger.debug(f"Grouped {len(sample_x_by_site)} DispatchTime records by site")

            if len(sample_x_by_site) != len(sample_results):
                logger.error(
                    "Mismatch between sample_x_by_site (%d) and sample_results (%d) lengths for sites: %s. Check data integrity.",
                    len(sample_x_by_site), len(sample_results), site_ids
                )

            dtos: List[DispatchTimeDistDTO] = []
            for gamma in gamma_results:
                dtos.append(DispatchTimeGammaDTO.from_orm_model(gamma))
            for sample in sample_results:
                sample_dispatch_hours_list = sample_x_by_site.get(sample.site_id, [])
                dtos.append(DispatchTimeSampleDTO.from_orm_model(sample_dispatch_hours_list, sample))

            confidence_level: float = session.query(Param.value).filter(Param.name == ParamName.DISPATCH_HIST_CONFIDENCE.value).scalar()
            logger.debug(f"Retrieved confidence level: {confidence_level}")

    except Exception:
        logger.exception("Exception during database query")
        raise

    adt_calculator: ADTCalculator = ADTCalculator()
    ddi_calculator: DDICalculator = DDICalculator(confidence_level=confidence_level)
    dt_indicators: List[Dict[str, Any]] = []

    for dto in dtos:
        adt_dto: ADT_DTO = adt_calculator.adt(dto)
        ddi_dto: DDI_DTO = ddi_calculator.ddi(dto)
        dt_indicators.append({
            "site": {
                "id": dto.site_id,
                "location": dto.site_location,
            },
            "supplier": {
                "id": dto.supplier_id,
                "manufacturer_id": dto.manufacturer_supplier_id,
                "name": dto.supplier_name,
            },
            "indicators": {
                "ADT": adt_dto.value,
                "DDI": {"lower": ddi_dto.lower, "upper": ddi_dto.upper, "confidence": confidence_level}
            }
        })

    return dt_indicators