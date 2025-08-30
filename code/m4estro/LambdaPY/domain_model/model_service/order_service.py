from typing import Dict, Any, List, Optional, Set

from sqlalchemy.orm import Query

from service.db_connector import DBConnector

from utils.parsing import parse_str_list
from service.db_utils import get_db_connector

from model.order import Order
from model.site import Site
from model_service.exception.order_not_found_exception import OrderNotFoundException

from model_dto.order_patch_dto import OrderPatchDTO
from model_dto.q_params import OrdersQParamsKeys, By

from logger import get_logger
logger = get_logger(__name__)

def _get_order_data(order: Order) -> Dict[str, Any]:
    return {
        "order_id": order.id,
        "manufacturer_order_id": order.manufacturer_order_id,
        "site": {
            "id": order.site_id,
            "location": order.site.location_name,
        },
        "supplier": {
            "id": order.site.supplier_id,
            "manufacturer_id": order.site.supplier.manufacturer_supplier_id,
            "name": order.site.supplier.name,
        },
        "carrier": {
            "id": order.carrier_id,
            "name": order.carrier.name
        },
        "tracking_number": order.tracking_number,
        "status": order.status,
        "SLS": order.SLS,
        "SRS": order.SRS,
    }

def get_orders(q_params: Dict[str, str] = {}) ->  List[Dict[str, Any]]:
    statuses: Set[str] = parse_str_list(q_params.get(OrdersQParamsKeys.STATUS.value, ""), case='upper')
    logger.debug(f"Parsed statuses from query parameters: {statuses}")

    connector: DBConnector = get_db_connector(read_only=True)
    try:
        with connector.session_scope() as session:
            orders: List[Order] = []
            if not statuses:
                logger.debug("No statuses provided, retrieving all orders")
                orders = session.query(Order).all()
            else:
                logger.debug(f"Retrieving orders with statuses: {statuses}")
                orders = session.query(Order).filter(Order.status.in_(statuses)).all()
            
            logger.debug(f"Retrieved {len(orders)} orders from the database")
            
            orders_json: List[Dict[str, Any]] = [_get_order_data(order) for order in orders]
            return orders_json
    except Exception:
        logger.exception("Exception during database query")
        raise

def get_order_by_id(order_id: int) ->  Dict[str, Any]:
    logger.debug(f"Retrieving order with ID: {order_id}")

    connector: DBConnector = get_db_connector(read_only=True)
    with connector.session_scope() as session:
        order: Order = session.query(Order).filter(Order.id == order_id).one_or_none()
        if not order:
            logger.debug(f"Order with ID {order_id} not found")
            raise OrderNotFoundException(f"Order with ID {order_id} not found")
        
        return _get_order_data(order)

def patch_order_by_id(id: int, by: By, patch: OrderPatchDTO) -> Dict[str, Any]:
    logger.debug(f"Patching order with ID: {id} by {by} with patch data: {patch}")

    connector: DBConnector = get_db_connector(read_only=False)    
    with connector.session_scope() as session:
        query: Query[Order] = session.query(Order)
        match by:
            case By.ID:
                query: Query[Order] = query.filter(Order.id == id)
                logger.debug(f"Filtering by order ID: {id}")
            case By.MANUFACTURER_ID:
                query: Query[Order] = query.filter(Order.manufacturer_order_id == id)
                logger.debug(f"Filtering by manufacturer order ID: {id}")

        order: Optional[Order] = query.one_or_none()
        if order is None:
            logger.debug(f"Order with ID {id} not found")
            raise OrderNotFoundException(f"Order with ID {id} not found")
        
        logger.debug(f"Order with ID {id} found, proceeding with patching")
        patch_order_timestamps(order, patch)

        site: Site = order.site
        patch_order_srs(order, site, patch)
        
        session.commit()
        logger.debug(f"Order with ID {id} patched successfully: {order}")
        
        return _get_order_data(order)

def patch_order_timestamps(order: Order, patch: OrderPatchDTO) -> None:
    logger.debug(f"Patching ID {order.id} with timestamps: {patch}")

    if patch.manufacturer_estimated_delivery is not None:
        order.manufacturer_estimated_delivery_timestamp = patch.manufacturer_estimated_delivery
        logger.debug(f"Updated manufacturer estimated delivery timestamp to {patch.manufacturer_estimated_delivery}")

    if patch.manufacturer_confirmed_delivery is not None:
        order.manufacturer_confirmed_delivery_timestamp = patch.manufacturer_confirmed_delivery
        logger.debug(f"Updated manufacturer confirmed delivery timestamp to {patch.manufacturer_confirmed_delivery}")

def patch_order_srs(order: Order, site: Site, patch: OrderPatchDTO) -> None:
    logger.debug(f"Patching SRS for order with ID: {order.id}")

    if patch.srs is None:
        return
    
    previous_srs: bool = order.SRS
    new_srs: bool = patch.srs
    if previous_srs == new_srs:
        logger.debug(f"No change in SRS for order ID {order.id}, current SRS: {previous_srs}")
        return
    
    order.SRS = new_srs
    logger.debug(f"Updated SRS for order ID {order.id} to {new_srs}")

    if new_srs:
        site.n_rejections += 1
        logger.debug(f"Incremented n_rejections for site {site.id} to {site.n_rejections}")
    else:
        site.n_rejections -= 1
        logger.debug(f"Decremented n_rejections for site {site.id} to {site.n_rejections}")