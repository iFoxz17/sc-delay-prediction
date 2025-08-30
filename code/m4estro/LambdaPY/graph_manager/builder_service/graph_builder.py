from typing import List, Optional, Tuple, Dict, Optional, Any
import igraph as ig

from service.read_only_db_connector import ReadOnlyDBConnector

from geo_calculator import GeoCalculator
from graph_config import (
    V_ID_ATTR,
    TYPE_ATTR,
    N_ORDERS_BY_CARRIER_ATTR,
    LATITUDE_ATTR,
    LONGITUDE_ATTR,
    DISTANCE_ATTR,
    AVG_ORI_ATTR,
    AVG_OTI_ATTR,
    AVG_WMI_ATTR,
    AVG_TMI_ATTR
)

from model.site import Site
from model.supplier import Supplier
from model.manufacturer import Manufacturer
from model.carrier import Carrier
from model.location import Location
from model.vertex import Vertex
from model.route import Route

from model.vertex import VertexType

from builder_service.query_handler import (
    QueryHandler,
    AvgVertexMetricResult,
    AvgRouteMetricResult,
    CarrierOrderCountResult,
    OrderRoutesResult
) 

from logger import get_logger
logger = get_logger(__name__)

class GraphBuilder:
    def __init__(self, db_connection_url: str, geo: Optional[GeoCalculator] = None) -> None:
        self.db_connection_url: str = db_connection_url
        
        self.geo: GeoCalculator = geo if geo else GeoCalculator()
        self.graph: ig.Graph = ig.Graph(directed=True)
    
    def build(self) -> ig.Graph:
        self.graph: ig.Graph = ig.Graph(directed=True)
        g: ig.Graph = self.graph
        connector: ReadOnlyDBConnector = ReadOnlyDBConnector(self.db_connection_url)

        try:
            with connector.session_scope() as session:
                query_handler: QueryHandler = QueryHandler(session)
                
                manufacturer: Manufacturer = query_handler.get_manufacturer()
                if not manufacturer:
                    logger.warning("No manufacturer found in the database, aborting graph build")
                    return g

                vertices: List[Vertex] = query_handler.get_all_vertices()
                routes: List[Route] = query_handler.get_all_routes()

                self._build_graph_topology(vertices, routes, manufacturer.name)
                logger.debug(f"Built graph topology: {len(g.vs)} vertices and {len(g.es)} edges")

                self._resolve_cycles()
                logger.debug(f"Resolved graph cycles: {len(g.es)} edges")

                locations: List[Location] = query_handler.get_all_locations()
                sites: List[Site] = query_handler.get_all_sites()

                self._set_companies_attributes(sites, manufacturer, locations)
                logger.debug("Companies attributes set successfully")                

                avg_ori_per_vertex: List[AvgVertexMetricResult] = query_handler.get_avg_ori_per_vertex()
                avg_oti_per_route: List[AvgRouteMetricResult] = query_handler.get_avg_oti_per_route()
                avg_tmi_per_route: List[AvgRouteMetricResult] = query_handler.get_avg_tmi_per_route()
                avg_wmi_per_route: List[AvgRouteMetricResult] = query_handler.get_avg_wmi_per_route()

                self._set_indicators_attributes(
                    avg_ori_per_vertex=avg_ori_per_vertex,
                    avg_oti_per_route=avg_oti_per_route,
                    avg_tmi_per_route=avg_tmi_per_route,
                    avg_wmi_per_route=avg_wmi_per_route
                )
                logger.debug("Indicators attributes set successfully")

                carriers: List[Carrier] = query_handler.get_all_carriers()
                n_orders_per_carrier_route: List[CarrierOrderCountResult] = query_handler.get_n_orders_per_carrier_route()
                order_routes: List[OrderRoutesResult] = query_handler.get_order_routes()

                self._set_orders_attributes(
                    carriers=carriers,
                    n_orders_per_carrier_route=n_orders_per_carrier_route,
                    order_routes=order_routes
                )

        except Exception:
            logger.exception("Error during graph building")
            raise
        
        return g
        
    def _build_graph_topology(self, vertices: list[Vertex], routes: list[Route], manufacturer_name: str) -> None:
        g: ig.Graph = self.graph  
        
        id_to_index: Dict[int, int] = {v.id: i for i, v in enumerate(vertices)}
        
        g.add_vertices(len(vertices))

        g.vs[V_ID_ATTR] = [v.id for v in vertices]
        g.vs["name"] = [v.name if v.type != VertexType.MANUFACTURER else manufacturer_name for v in vertices]
        g.vs[TYPE_ATTR] = [v.type.value for v in vertices]

        edges: List[Tuple[int, int]] = [
            (id_to_index[r.source_id], id_to_index[r.destination_id])
            for r in routes
        ]
        g.add_edges(edges)
    
    def _resolve_cycles(self) -> None:
        g = self.graph

        if not g.is_dag():
            logger.error("Graph is not a DAG, cycles need to be resolved")
    
    def _set_companies_attributes(self, sites: List[Site], manufacturer: Manufacturer, locations: List[Location]) -> None:
        g = self.graph
        geo = self.geo
        
        sites_by_id: Dict[int, Site] = {site.id: site for site in sites}
        locations_by_name: Dict[str, Location] = {loc.name: loc for loc in locations}

        manufacturer_location: Location = manufacturer.location

        for v in g.vs:
            if v[TYPE_ATTR] == VertexType.SUPPLIER_SITE.value:
                site_id: int = int(v['name'])
                site: Site = sites_by_id.get(site_id)
                if not site:
                    logger.error(f"Site not found for vertex {v.index} with id {v['v_id']} and name {v['name']}")
                    continue
                v["site_id"] = site.id

                supplier: Supplier = site.supplier
                v["company_id"] = supplier.id
                v['company_name'] = supplier.name
                v["manufacturer_supplier_id"] = supplier.manufacturer_supplier_id

                v["n_rejections"] = site.n_rejections
                v["n_orders"] = site.n_orders
                
                model_location: Location = site.location
                v["location"] = model_location.name
                v["receiver_distance"] = geo.geodesic_distance(
                    model_location.latitude, model_location.longitude,
                    manufacturer_location.latitude, manufacturer_location.longitude
                )
                v[LATITUDE_ATTR] = model_location.latitude
                v[LONGITUDE_ATTR] = model_location.longitude
            
            elif v[TYPE_ATTR] == VertexType.INTERMEDIATE.value:
                location: str = locations_by_name.get(v['name'])
                if not location:
                    logger.error(f"Location not found for vertex {v.index} with id {v['v_id']} and name {v['name']}")
                    continue

                v["location"] = location.name
                v["receiver_distance"] = geo.geodesic_distance(
                    location.latitude, location.longitude,
                    manufacturer_location.latitude, manufacturer_location.longitude
                )
                v[LATITUDE_ATTR] = location.latitude
                v[LONGITUDE_ATTR] = location.longitude

            elif v[TYPE_ATTR] == VertexType.MANUFACTURER.value:
                v["company_id"] = manufacturer.id
                v['company_name'] = manufacturer.name

                v["location"] = manufacturer_location.name
                v["receiver_distance"] = 0.0
                v[LATITUDE_ATTR] = manufacturer_location.latitude
                v[LONGITUDE_ATTR] = manufacturer_location.longitude
                
            else:
                logger.error(f"Unknown vertex type: {v['type']} for vertex {v.index} with id {v[V_ID_ATTR]} and name {v['name']}. This should never happen")
        
    def _set_indicators_attributes(self,
                               avg_ori_per_vertex: List[AvgVertexMetricResult], 
                               avg_oti_per_route: List[AvgRouteMetricResult],
                               avg_tmi_per_route: List[AvgRouteMetricResult],
                               avg_wmi_per_route: List[AvgRouteMetricResult]
                               ) -> None:
        g = self.graph
        geo = self.geo

        avg_ori_by_vertex: Dict[int, float] = {m.vertex_id: m.value for m in avg_ori_per_vertex}
        for v in g.vs:
            if v[TYPE_ATTR] != VertexType.INTERMEDIATE.value:
                v[AVG_ORI_ATTR] = 0.0
                continue
            
            avg_ori: Optional[float] = avg_ori_by_vertex.get(v[V_ID_ATTR])
            if avg_ori is None:
                logger.info(f"No average ORI found for vertex {v.index} with id {v[V_ID_ATTR]} and name {v['name']}: setting to 0.0")

            v[AVG_ORI_ATTR] = avg_ori or 0.0    

        avg_oti_by_route: Dict[Tuple[int, int], float] = {(m.source_id, m.destination_id): m.value for m in avg_oti_per_route}
        avg_tmi_by_route: Dict[Tuple[int, int], float] = {(m.source_id, m.destination_id): m.value for m in avg_tmi_per_route}
        avg_wmi_by_route: Dict[Tuple[int, int], float] = {(m.source_id, m.destination_id): m.value for m in avg_wmi_per_route}

        for e in g.es:
            source_v: ig.Vertex = g.vs[e.source]
            source_id: int = source_v[V_ID_ATTR]
            source_name: str = source_v['name']

            dest_v: ig.Vertex = g.vs[e.target]
            dest_id: int = dest_v[V_ID_ATTR]
            dest_name: str = dest_v['name']
            
            e[DISTANCE_ATTR] = geo.geodesic_distance(
                source_v[LATITUDE_ATTR], source_v[LONGITUDE_ATTR],
                dest_v[LATITUDE_ATTR], dest_v[LONGITUDE_ATTR]
            )

            avg_oti: Optional[float] = avg_oti_by_route.get((source_id, dest_id))
            if avg_oti is None:
                logger.info(f"No average OTI found for edge {e.index} from {source_name} (v_id={source_id}) to {dest_name} (v_id={dest_id}): setting to 0.0")

            avg_tmi: Optional[float] = avg_tmi_by_route.get((source_id, dest_id))
            if avg_tmi is None:
                logger.info(f"No average TMI found for edge {e.index} from {source_name} (v_id={source_id}) to {dest_name} (v_id={dest_id}): setting to 0.0")

            avg_wmi: Optional[float] = avg_wmi_by_route.get((source_id, dest_id))
            if avg_wmi is None:
                logger.info(f"No average WMI found for edge {e.index} from {source_name} (v_id={source_id}) to {dest_name} (v_id={dest_id}): setting to 0.0")

            e[AVG_OTI_ATTR] = avg_oti or 0.0
            e[AVG_TMI_ATTR] = avg_tmi or 0.0
            e[AVG_WMI_ATTR] = avg_wmi or 0.0

    def _set_orders_attributes(self,
        carriers: List[Carrier],
        n_orders_per_carrier_route: List[CarrierOrderCountResult],
        order_routes: List[OrderRoutesResult]
        ) -> None:
        
        g = self.graph

        n_orders_by_route = {
            (cocr.source_id, cocr.destination_id, cocr.carrier_id): cocr.route_carrier_orders_count
            for cocr in n_orders_per_carrier_route
        }

        carriers_by_id: Dict[int, Carrier] = {c.id: c for c in carriers}

        for v in g.vs:
            v[N_ORDERS_BY_CARRIER_ATTR] = {} 
            v['orders'] = []
            v['n_orders'] = 0

        for e in g.es:
            e[N_ORDERS_BY_CARRIER_ATTR] = {}
            e['orders'] = []
            e['n_orders'] = 0

        for (source_id, dest_id, carrier_id), count in n_orders_by_route.items():
            try:
                source_vertex: ig.Vertex = g.vs.find(v_id=source_id)
            except ValueError as e:
                logger.error(f"Source vertex not found for route from v_id={source_id} to v_id={dest_id}: {e}")
                continue

            try:
                dest_vertex: ig.Vertex = g.vs.find(v_id=dest_id)
            except ValueError as e:
                logger.error(f"Destination vertex not found for route from v_id={source_id} to v_id={dest_id}: {e}")
                continue

            edge_id: int = g.get_eid(source_vertex.index, dest_vertex.index, error=False)
            if edge_id == -1:
                logger.error(f"Edge not found for route from v_id={source_id} ({source_vertex['name']}) to v_id={dest_id} ({dest_vertex['name']})")
                continue

            edge: ig.Edge = g.es[edge_id]

            carrier: Optional[Carrier] = carriers_by_id.get(carrier_id)
            if carrier is None:
                logger.error(f"Carrier with id {carrier_id} not found for route {source_id} ({source_vertex['name']}) -> {dest_id} ({dest_vertex['name']})")
                continue
            carrier_name: str = carrier.name

            # Update vertex-level counts
            source_n_orders_by_carrier: Dict[str, int] = source_vertex[N_ORDERS_BY_CARRIER_ATTR]
            source_n_orders_by_carrier[carrier_name] = source_n_orders_by_carrier.get(carrier_name, 0) + count
            source_vertex['n_orders'] += count
            
            if dest_vertex[TYPE_ATTR] == VertexType.MANUFACTURER.value:                # Update only if destination is the sink vertex
                dest_n_orders_by_carrier: Dict[str, int] = dest_vertex[N_ORDERS_BY_CARRIER_ATTR]
                dest_n_orders_by_carrier[carrier_name] = dest_n_orders_by_carrier.get(carrier_name, 0) + count
                dest_vertex['n_orders'] += count  

            # Update edge-level counts
            edge_n_orders_by_carrier: Dict[str, int] = edge[N_ORDERS_BY_CARRIER_ATTR]
            edge_n_orders_by_carrier[carrier_name] = edge_n_orders_by_carrier.get(carrier_name, 0) + count
            edge['n_orders'] += count

        for orr in order_routes:
            source_id, dest_id = orr.source_id, orr.destination_id
            
            try:
                source_vertex: ig.Vertex = g.vs.find(v_id=source_id)
            except ValueError as e:
                logger.error(f"Source vertex not found for route from v_id={source_id} to v_id={dest_id}: {e}")
                continue

            try:
                dest_vertex: ig.Vertex = g.vs.find(v_id=dest_id)
            except ValueError as e:
                logger.error(f"Destination vertex not found for route from v_id={source_id} to v_id={dest_id}: {e}")
                continue

            edge_id: int = g.get_eid(source_vertex.index, dest_vertex.index, error=False)
            if edge_id == -1:
                logger.error(f"Edge not found for route from v_id={source_id} ({source_vertex['name']}) to v_id={dest_id} ({dest_vertex['name']})")
                continue

            edge: ig.Edge = g.es[edge_id]

            carrier: Optional[Carrier] = carriers_by_id.get(orr.carrier_id)
            if carrier is None:
                logger.error(f"Carrier with id {orr.carrier_id} not found for route {source_id} ({source_vertex['name']}) -> {dest_id} ({dest_vertex['name']})")
                continue
            carrier_name: str = carrier.name

            order_data: Dict[str, Any] = {
                "order_id": orr.order_id,
                "manufacturer_order_id": orr.manufacturer_order_id,
                "tracking_number": orr.tracking_number,
                "carrier_name": carrier_name
            }

            source_vertex['orders'].append(order_data)
            dest_vertex['orders'].append(order_data)
            edge['orders'].append(order_data)