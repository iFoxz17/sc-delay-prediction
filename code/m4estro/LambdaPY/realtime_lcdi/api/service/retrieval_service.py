from typing import Set, Dict, Any, List, TYPE_CHECKING
from sqlalchemy.orm import joinedload
from collections import defaultdict

from utils.config import get_env, DATABASE_SECRET_ARN_KEY, AWS_REGION_KEY
from utils.parsing import parse_id_list

from service.read_only_db_connector import ReadOnlyDBConnector
from service.db_utils import get_read_only_db_connector

from api.dto.qparam import RealtimeQParamKeys

from core.formatter.formatter import Formatter, EstimatedTimeSharedDTO

from model.estimated_time import EstimatedTime
from model.order import Order
from model.site import Site
from model.manufacturer import Manufacturer

if TYPE_CHECKING:
    from model.supplier import Supplier
    from model.time_deviation import TimeDeviation

from logger import get_logger
logger = get_logger(__name__)

def get_realtime_lcdi_by_order(query_params: Dict[str, str]) -> List[Dict[str, Any]] | Dict[str, Any]:
    order_param: str = query_params.get(RealtimeQParamKeys.ORDER.value, '')
    order_ids: Set[int] = parse_id_list(order_param)
    logger.debug(f"Order query parameter: {order_param} -> IDs: {order_ids or 'ALL'}")

    formatter: Formatter = Formatter()

    ro_db_connector: ReadOnlyDBConnector = get_read_only_db_connector()
    with ro_db_connector.session_scope() as session:
        # Eagerly load all relevant relationships to avoid N+1 queries
        query = session.query(EstimatedTime).options(
            joinedload(EstimatedTime.order).joinedload(Order.carrier),
            joinedload(EstimatedTime.order).joinedload(Order.site).joinedload(Site.supplier),
            joinedload(EstimatedTime.order).joinedload(Order.manufacturer),
            joinedload(EstimatedTime.vertex),
            joinedload(EstimatedTime.time_deviation),
            joinedload(EstimatedTime.alpha)
        )

        if order_ids:
            query = query.filter(EstimatedTime.order_id.in_(order_ids))

        estimated_times: List[EstimatedTime] = query.all()
        logger.debug(f"Retrieved {len(estimated_times)} estimated time records")

        et_grouped_by_order: Dict[int, List[EstimatedTime]] = defaultdict(list)
        for et in estimated_times:
            et_grouped_by_order[et.order_id].append(et)
        logger.debug(f"Grouped estimated times records by: {len(et_grouped_by_order)} orders")

        for et in et_grouped_by_order.values():
            et.sort(key=lambda x: x.estimation_time, reverse=False)

        data: List[Dict[str, Any]] = []
        for order_id, ets in et_grouped_by_order.items():
            ets_last: EstimatedTime = ets[-1]
            order: Order = ets_last.order
            site: Site = order.site
            supplier: Supplier = site.supplier
            manufacturer: Manufacturer = order.manufacturer
            time_deviation: 'TimeDeviation' = ets_last.time_deviation

            shared: EstimatedTimeSharedDTO = EstimatedTimeSharedDTO(
                order_id=order_id,
                manufacturer_order_id=order.manufacturer_order_id,      #TODO: Adjust model to set this field not nullable
                tracking_number=order.tracking_number,
                carrier_id=order.carrier.id,
                carrier_name=order.carrier.name,
                site_id=site.id,
                site_location=site.location.name,
                supplier_id=supplier.id,
                manufacturer_supplier_id=supplier.manufacturer_supplier_id,
                supplier_name=supplier.name,
                manufacturer_id=manufacturer.id,
                manufacturer_name=manufacturer.name,
                manufacturer_location=manufacturer.location_name,
                SLS=order.SLS,
                SRS=order.SRS,
                EODT=ets_last.EODT,
                EDD=ets_last.EDD,
                dispatch_td_lower=time_deviation.dt_hours_lower,
                dispatch_td_upper=time_deviation.dt_hours_upper,
                shipment_td_lower=time_deviation.st_hours_lower,
                shipment_td_upper=time_deviation.st_hours_upper,
                status=order.status
            )

            data.append(formatter.format_et_by_order(shared, ets))

    return data[0] if len(data) == 1 else data



