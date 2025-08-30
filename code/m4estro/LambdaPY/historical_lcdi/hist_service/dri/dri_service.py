from typing import Any, Set, List, Dict

from service.read_only_db_connector import ReadOnlyDBConnector
from service.db_utils import get_read_only_db_connector

from utils.parsing import parse_id_list

from model.site import Site

from hist_service.dri.dri_calculator import DRICalculator
from hist_service.dri.dri_dto import DRI_DTO

from historical_api.q_params import HistoricalQParamsKeys

from logger import get_logger
logger = get_logger(__name__)

def calculate_dri(query_params: Dict[str, str]) -> list[Dict[str, Any]]:
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

            site_results: List[Site] = session.query(Site).filter(Site.id.in_(site_ids)).all()
            logger.debug(f"Retrieved {len(site_results)} sites for DRI calculation")

            dri_calculator: DRICalculator = DRICalculator()
            dri_indicators: List[Dict[str, Any]] = []
            
            for site in site_results:
                dri: DRI_DTO = dri_calculator.calculate_dri(n_rejections=site.n_rejections, n_orders=site.n_orders)

                dri_indicators.append({
                    "site": {
                        "id": site.id,
                        "location": site.location_name,
                    },
                    "supplier": {
                        "id": site.supplier_id,
                        "manufacturer_id": site.supplier.manufacturer_supplier_id,
                        "name": site.supplier.name
                    },
                    "indicators": {
                        "DRI": dri.value
                        }
                    })
            logger.debug(f"Calculated DRI indicators for {len(dri_indicators)} sites")

            return dri_indicators
    except Exception:
        logger.exception("Exception during database query")
        raise