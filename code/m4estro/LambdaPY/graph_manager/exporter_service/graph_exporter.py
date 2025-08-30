from typing import Dict, Any, List, Optional
import igraph as ig

from model.vertex import VertexType

from geo_calculator import GeoCalculator
from graph_config import (
    V_ID_ATTR,
    TYPE_ATTR,
    N_ORDERS_BY_CARRIER_ATTR,
    LATITUDE_ATTR,
    LONGITUDE_ATTR,
    AVG_ORI_ATTR,
    DISTANCE_ATTR,
    AVG_OTI_ATTR,
    AVG_WMI_ATTR,
    AVG_TMI_ATTR,
)

class GraphExporter:
    def __init__(self, geo: Optional[GeoCalculator] = None) -> None:
        self.geo: GeoCalculator = geo or GeoCalculator()

    def export_as_graph(self, graph: ig.Graph) -> Dict[str, Any]:
        vertex_data: List = []
        edge_data: List = []
        for vertex in graph.vs:
            vertex_data.append({
                "v_id": vertex[V_ID_ATTR],
                "name": vertex['name'],
                "type": vertex[TYPE_ATTR],
                "location": vertex['location'],
                "receiver_distance": vertex['receiver_distance'],
                "coordinates": [float(vertex[LATITUDE_ATTR]), float(vertex[LONGITUDE_ATTR])],

                "site_id": vertex['site_id'],
                "company_id": vertex['company_id'],
                "company_name": vertex['company_name'],
                "manufacturer_supplier_id": vertex['manufacturer_supplier_id'],

                "packages": vertex['orders'],
                "n_orders_by_carrier": vertex[N_ORDERS_BY_CARRIER_ATTR],
                "n_orders": vertex['n_orders'],
                "n_rejections": vertex['n_rejections'],

                "avg_ORI": vertex[AVG_ORI_ATTR],
            })

        for edge in graph.es:
            s_v = graph.vs[edge.source]
            t_v = graph.vs[edge.target]

            edge_data.append({
                "source": s_v['v_id'],
                "target":  t_v['v_id'],
                
                "packages": edge['orders'],
                "n_orders_by_carrier": edge[N_ORDERS_BY_CARRIER_ATTR],
                "n_orders": edge['n_orders'],

                "distance": edge[DISTANCE_ATTR],
                "avg_OTI": edge[AVG_OTI_ATTR],
                "avg_WMI": edge[AVG_WMI_ATTR],
                "avg_TMI": edge[AVG_TMI_ATTR],
            })

        return {
            "nodes": vertex_data,
            "links": edge_data,
        }

    def export_as_map(self, graph: ig.Graph) -> Dict[str, Any]:
        intermediate_vertices: List[int] = [v.index for v in graph.vs if v[TYPE_ATTR] == VertexType.INTERMEDIATE.value]
        graph.delete_vertices(intermediate_vertices)

        manufacturer_v: ig.Vertex = graph.vs.find(type=VertexType.MANUFACTURER.value)

        vertex_data: List = []
        edge_data: List = []

        for vertex in graph.vs:
            vertex_data.append({
                "v_id": vertex[V_ID_ATTR],
                "name": vertex['name'],
                "type": vertex[TYPE_ATTR],
                "location": vertex['location'],
                "receiver_distance": vertex['receiver_distance'],
                "coordinates": [vertex[LATITUDE_ATTR], vertex[LONGITUDE_ATTR]],

                "site_id": vertex['site_id'],
                "company_id": vertex['company_id'],
                "company_name": vertex['company_name'],
                "manufacturer_supplier_id": vertex['manufacturer_supplier_id'],

                "packages": vertex['orders'],
                "n_orders_by_carrier": vertex[N_ORDERS_BY_CARRIER_ATTR],
                "n_orders": vertex['n_orders'],
                "n_rejections": vertex['n_rejections'],
            })

            if vertex != manufacturer_v:
                edge_data.append({
                    "source": vertex['v_id'],
                    "target": manufacturer_v['v_id'],

                    "packages": vertex['orders'],
                    "n_orders_by_carrier": vertex[N_ORDERS_BY_CARRIER_ATTR],
                    "n_orders": vertex['n_orders'],

                    "distance": self.geo.geodesic_distance(
                        vertex[LATITUDE_ATTR], vertex[LONGITUDE_ATTR],
                        manufacturer_v[LATITUDE_ATTR], manufacturer_v[LONGITUDE_ATTR]
                    ),
                })

        return {
            "nodes": vertex_data,
            "links": edge_data,
        }

        
            

