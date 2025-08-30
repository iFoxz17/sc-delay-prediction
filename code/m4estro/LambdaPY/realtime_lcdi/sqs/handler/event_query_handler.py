from typing import TYPE_CHECKING
from sqlalchemy.orm import joinedload

from model.order import Order

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

class EventQueryHandler:
    def __init__(self, session: 'Session') -> None:
        self.session: 'Session' = session

    def get_order_by_id(self, id: int) -> Order:
        return self.session.query(Order).options(joinedload(Order.manufacturer)).filter(Order.id == id).one()

    def get_order_by_tracking_number(self, tracking_number: str) -> Order:
        return self.session.query(Order).filter(Order.tracking_number == tracking_number).one()