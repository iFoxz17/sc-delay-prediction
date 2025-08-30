from typing import List, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Float, Row

from model.manufacturer import Manufacturer
from model.vertex import Vertex
from model.route import Route
from model.location import Location
from model.site import Site
from model.carrier import Carrier
from model.route_order import RouteOrder
from model.order import Order
from model.ori import ORI
from model.oti import OTI
from model.tmi import TMI
from model.wmi import WMI

@dataclass
class AvgVertexMetricResult:
    vertex_id: int
    value: float

@dataclass
class AvgRouteMetricResult:
    source_id: int
    destination_id: int
    value: float

@dataclass
class CarrierOrderCountResult:
    source_id: int
    destination_id: int
    carrier_id: int
    route_carrier_orders_count: int

@dataclass
class OrderRoutesResult:
    source_id: int
    destination_id: int
    order_id: int
    manufacturer_order_id: int
    tracking_number: str
    carrier_id: int

class QueryHandler:
    def __init__(self, session: Session):
        self.session = session

    def get_manufacturer(self) -> Manufacturer:
        return self.session.query(Manufacturer).first()

    def get_all_vertices(self) -> List[Vertex]:
        return self.session.query(Vertex).all()

    def get_all_routes(self) -> List[Route]:
        return self.session.query(Route).all()

    def get_all_locations(self) -> List[Location]:
        return self.session.query(Location).all()

    def get_all_sites(self) -> List[Site]:
        return self.session.query(Site).all()

    def get_all_carriers(self) -> List[Carrier]:
        return self.session.query(Carrier).all()

    def get_avg_ori_per_vertex(self) -> List[AvgVertexMetricResult]:
        result: List[Row[Tuple[int, float]]] = (
            self.session.query(
                ORI.vertex_id,
                cast(func.avg(ORI.hours), Float).label("avg_ori")
            )
            .group_by(ORI.vertex_id)
            .all()
        )
        return [AvgVertexMetricResult(vertex_id=row[0], value=row[1]) for row in result]

    def get_avg_oti_per_route(self) -> List[AvgRouteMetricResult]:
        result: List[Row[Tuple[int, int, float]]] = (
            self.session.query(
                OTI.source_id,
                OTI.destination_id,
                cast(func.avg(OTI.hours), Float).label("avg_oti")
            )
            .group_by(OTI.source_id, OTI.destination_id)
            .all()
        )
        return [AvgRouteMetricResult(source_id=row[0], destination_id=row[1], value=row[2]) for row in result]

    def get_avg_tmi_per_route(self) -> List[AvgRouteMetricResult]:
        result: List[Row[Tuple[int, int, float]]] = (
            self.session.query(
                TMI.source_id,
                TMI.destination_id,
                cast(func.avg(TMI.value), Float).label("avg_tmi")
            )
            .group_by(TMI.source_id, TMI.destination_id)
            .all()
        )
        return [AvgRouteMetricResult(source_id=row[0], destination_id=row[1], value=row[2]) for row in result]

    def get_avg_wmi_per_route(self) -> List[AvgRouteMetricResult]:
        result: List[Row[Tuple[int, int, float]]] = (
            self.session.query(
                WMI.source_id,
                WMI.destination_id,
                cast(func.avg(WMI.value), Float).label("avg_wmi")
            )
            .group_by(WMI.source_id, WMI.destination_id)
            .all()
        )
        return [AvgRouteMetricResult(source_id=row[0], destination_id=row[1], value=row[2]) for row in result]

    def get_n_orders_per_carrier_route(self) -> List[CarrierOrderCountResult]:
        result: List[Row[Tuple[int, int, int, int]]] = (
            self.session.query(
                RouteOrder.source_id,
                RouteOrder.destination_id,
                Order.carrier_id,
                func.count(RouteOrder.id).label("route_carrier_orders_count")
            )
            .join(Order, RouteOrder.order_id == Order.id)
            .group_by(RouteOrder.source_id, RouteOrder.destination_id, Order.carrier_id)
            .all()
        )
        return [CarrierOrderCountResult(source_id=row[0], destination_id=row[1], carrier_id=row[2], route_carrier_orders_count=row[3]) for row in result]
    
    def get_order_routes(self) -> List[OrderRoutesResult]:
        result: List[Row[Tuple[int, int, int, Optional[int], str, int]]] = (
            self.session.query(
                RouteOrder.source_id,
                RouteOrder.destination_id,
                Order.id.label("order_id"),
                Order.manufacturer_order_id.label("manufacturer_order_id"),
                Order.tracking_number.label("tracking_number"),
                Order.carrier_id.label("carrier_id")
            )
            .join(Order, RouteOrder.order_id == Order.id)
            .all()
        )
        return [OrderRoutesResult(source_id=row[0], destination_id=row[1], order_id=row[2], manufacturer_order_id=row[3], tracking_number=row[4], carrier_id=row[5]) for row in result]