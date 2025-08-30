import pytest
import igraph as ig
from collections import defaultdict
from dataclasses import astuple

from contextlib import contextmanager

from service.read_only_db_connector import ReadOnlyDBConnector
from geo_calculator import GeoCalculator

from model.vertex import Vertex, VertexType
from model.route import Route
from model.site import Site
from model.supplier import Supplier
from model.carrier import Carrier
from model.manufacturer import Manufacturer
from model.location import Location

from graph_config import N_ORDERS_BY_CARRIER_ATTR, V_ID_ATTR, TYPE_ATTR

from builder_service.query_handler import AvgVertexMetricResult, AvgRouteMetricResult, CarrierOrderCountResult, OrderRoutesResult
from builder_service.graph_builder import GraphBuilder

from model.vertex import VertexType

# Helper to create a Vertex
def make_vertex(id: int, name: str, vtype: VertexType) -> Vertex:
    vertex = Vertex()
    vertex.id = id
    vertex.name = name
    vertex.type = vtype
    return vertex

# Helper to create a Route
def make_route(id: int, source_id: int, dest_id: int) -> Route:
    route = Route()
    route.id = id
    route.source_id = source_id
    route.destination_id = dest_id
    return route

def make_route_order(id: int, source_id: int, dest_id: int, order_id: int) -> Route:
    route_order = Route()
    route_order.id = id
    route_order.source_id = source_id
    route_order.destination_id = dest_id
    route_order.order_id = order_id
    return route_order


@pytest.fixture(scope="module")
def supply_chain_test_data():
    # Locations - one per vertex
    locations = {
        "Site-1": Location(id=1, name="Location-Site-1", latitude=45.0, longitude=7.0),
        "Site-2": Location(id=2, name="Location-Site-2", latitude=45.1, longitude=7.1),
        "Site-3": Location(id=3, name="Location-Site-3", latitude=45.2, longitude=7.2),

        "Intermediate-1": Location(id=4, name="Location-Intermediate-1", latitude=46.0, longitude=8.0),
        "Intermediate-2": Location(id=5, name="Location-Intermediate-2", latitude=46.1, longitude=8.1),
        "Intermediate-3": Location(id=6, name="Location-Intermediate-3", latitude=46.2, longitude=8.2),
        "Intermediate-4": Location(id=7, name="Location-Intermediate-4", latitude=46.3, longitude=8.3),
        "Intermediate-5": Location(id=8, name="Location-Intermediate-5", latitude=46.4, longitude=8.4),
        "Intermediate-6": Location(id=9, name="Location-Intermediate-6", latitude=46.5, longitude=8.5),

        "Manufacturer": Location(id=10, name="Location-Manufacturer", latitude=47.0, longitude=9.0),
    }

    # Carriers
    carriers = {
        "Carrier-1": Carrier(id=1, name="Carrier-1", carrier_17track_id="10000"),
        "Carrier-2": Carrier(id=2, name="Carrier-2", carrier_17track_id="20000"),
        "Carrier-3": Carrier(id=3, name="Carrier-3", carrier_17track_id="30000"),
    }

    # Suppliers for each supplier vertex
    suppliers = {
        "Supplier-A": Supplier(id=1, name="SupplierCo-A"),
        "Supplier-B": Supplier(id=2, name="SupplierCo-B"),
    }

    # Sites for each supplier
    sites = [
        Site(id=1, supplier_id=1, supplier=suppliers["Supplier-A"], location=locations["Site-1"], n_rejections=3, n_orders=15),
        Site(id=2, supplier_id=1, supplier=suppliers["Supplier-A"], location=locations["Site-2"], n_rejections=1, n_orders=9),
        Site(id=3, supplier_id=2, supplier=suppliers["Supplier-B"], location=locations["Site-3"], n_rejections=2, n_orders=12),
    ]

    # Manufacturer object with location
    manufacturer = Manufacturer(
        id=1,
        name="Manufacturer",
        location=locations["Manufacturer"]
    )

    # Vertices
    site_vertices = [
        make_vertex(1, "1", VertexType.SUPPLIER_SITE),        # Site 1
        make_vertex(2, "2", VertexType.SUPPLIER_SITE),        # Site 2
        make_vertex(3, "3", VertexType.SUPPLIER_SITE),        # Site 3
    ]

    intermediate_vertices = [
        make_vertex(4, locations["Intermediate-1"].name, VertexType.INTERMEDIATE),
        make_vertex(5, locations["Intermediate-2"].name, VertexType.INTERMEDIATE),
        make_vertex(6, locations["Intermediate-3"].name, VertexType.INTERMEDIATE),
        make_vertex(7, locations["Intermediate-4"].name, VertexType.INTERMEDIATE),
        make_vertex(8, locations["Intermediate-5"].name, VertexType.INTERMEDIATE),
        make_vertex(9, locations["Intermediate-6"].name, VertexType.INTERMEDIATE),
    ]

    manufacturer_vertex = make_vertex(10, "1", VertexType.MANUFACTURER)

    vertices = site_vertices + intermediate_vertices + [manufacturer_vertex]

    # Routes
    routes = [
        make_route(1, 1, 4),
        make_route(2, 2, 4),
        make_route(3, 3, 5),
        make_route(4, 4, 6),
        make_route(5, 4, 5),
        make_route(5, 5, 6),
        make_route(6, 6, 7),
        make_route(7, 7, 8),
        make_route(8, 8, 9),
        make_route(9, 9, 10),
    ]

    n_orders_per_carrier_route = [
        CarrierOrderCountResult(*t) for t in [
            (1, 4, 1, 10), (4, 6, 1, 10), (6, 7, 1, 10), (7, 8, 1, 10), (8, 9, 1, 10), (9, 10, 1, 10),
            (1, 4, 2, 5), (3, 5, 2, 12), (4, 6, 2, 5), (5, 6, 2, 12),
            (6, 7, 2, 17), (7, 8, 2, 17), (8, 9, 2, 17), (9, 10, 2, 17),
            (2, 4, 3, 9),
            (4, 5, 3, 7), (4, 6, 3, 2), (5, 6, 3, 7),
            (6, 7, 3, 9), (7, 8, 3, 9), (8, 9, 3, 9), (9, 10, 3, 9),
        ]
    ]

    order_routes_data = [
        OrderRoutesResult(source_id, dest_id, order_id, manufacturer_order_id, str(manufacturer_order_id), carrier_id)
        for (source_id, dest_id, carrier_id, manufacturer_order_id, order_id) in [
            (1, 4, 1, 100, 1), (4, 6, 1, 100, 1), (6, 7, 1, 100, 1), (7, 8, 1, 100, 1), (8, 9, 1, 100, 1), (9, 10, 1, 100, 1),
            (1, 4, 2, 101, 2), (3, 5, 2, 101, 2), (4, 6, 2, 101, 2), (5, 6, 2, 101, 2),
            (6, 7, 2, 101, 2), (7, 8, 2, 101, 2), (8, 9, 2, 101, 2), (9, 10, 2, 101, 2),
            (2, 4, 3, 102, 3), (4, 5, 3, 102, 3), (4, 6, 3, 102, 3), (5, 6, 3, 102, 3),
            (6, 7, 3, 102, 3), (7, 8, 3, 102, 3), (8, 9, 3, 102, 3), (9, 10, 3, 102, 3),
        ]
    ]

    avg_ori_per_vertex = [
        AvgVertexMetricResult(*t) for t in [
            (1, 0.0), (2, 0.0), (3, 0.0), (4, 0.85), (5, 0.60), (6, 0.70),
            (7, 0.80), (8, 0.90), (9, 0.95), (10, 0.00),
        ]
    ]

    avg_oti_per_route = [
        AvgRouteMetricResult(*t) for t in [
            (1, 4, 1.05), (2, 4, 1.10), (3, 5, 1.15), (4, 5, 1.10), (4, 6, 1.20),
            (5, 6, 1.25), (6, 7, 1.30), (7, 8, 1.35), (8, 9, 1.40), (9, 10, 1.45),
        ]
    ]

    avg_tmi_per_route = [
        AvgRouteMetricResult(*t) for t in [
            (1, 4, 0.55), (2, 4, 0.60), (3, 5, 0.65), (4, 5, 0.50), (4, 6, 0.70),
            (5, 6, 0.75), (6, 7, 0.80), (7, 8, 0.85), (8, 9, 0.90), (9, 10, 0.95),
        ]
    ]

    avg_wmi_per_route = [
        AvgRouteMetricResult(*t) for t in [
            (1, 4, 0.90), (2, 4, 0.85), (3, 5, 0.80), (4, 5, 0.75), (4, 6, 0.75),
            (5, 6, 0.70), (6, 7, 0.65), (7, 8, 0.60), (8, 9, 0.55), (9, 10, 0.50),
        ]
    ]

    # Extend the return dict with the indicators
    return {
        "vertices": vertices,
        "routes": routes,
        "n_orders_per_carrier_route": n_orders_per_carrier_route,
        "order_routes_data": order_routes_data,
        "sites": sites,
        "suppliers": suppliers,
        "manufacturer": manufacturer,
        "carriers": carriers,
        "locations": list(locations.values()),
        "avg_ori_per_vertex": avg_ori_per_vertex,
        "avg_oti_per_route": avg_oti_per_route,
        "avg_tmi_per_route": avg_tmi_per_route,
        "avg_wmi_per_route": avg_wmi_per_route,
    }


def test_build_graph_topology_basic(supply_chain_test_data):
    vertices: list[Vertex] = supply_chain_test_data["vertices"]
    routes: list[Route] = supply_chain_test_data["routes"]

    manufacturer: Manufacturer = supply_chain_test_data["manufacturer"]
    manufacturer_name = manufacturer.name

    builder = GraphBuilder("db_connection_string")
    builder.graph = ig.Graph(directed=True)
    builder._build_graph_topology(vertices, routes, manufacturer_name)
    g: ig.Graph = builder.graph

    assert len(g.vs) == 10
    assert len(g.es) == 10

    assert g.vs[TYPE_ATTR].count(VertexType.SUPPLIER_SITE.value) == 3
    assert g.vs[TYPE_ATTR].count(VertexType.INTERMEDIATE.value) == 6
    assert g.vs[TYPE_ATTR].count(VertexType.MANUFACTURER.value) == 1

    assert manufacturer_name in g.vs["name"]
    manufacturer_index = g.vs["name"].index(manufacturer_name)
    assert g.vs[manufacturer_index][TYPE_ATTR] == VertexType.MANUFACTURER.value

    name_edges = [(g.vs[e.source]["name"], g.vs[e.target]["name"]) for e in g.es]
    assert ("1", "Location-Intermediate-1") in name_edges
    assert ("Location-Intermediate-6", manufacturer_name) in name_edges
    assert ("2", "Location-Intermediate-1") in name_edges
    assert ("3", "Location-Intermediate-2") in name_edges
    assert ("Location-Intermediate-1", "Location-Intermediate-3") in name_edges
    assert ("Location-Intermediate-2", "Location-Intermediate-3") in name_edges
    assert ("Location-Intermediate-3", "Location-Intermediate-4") in name_edges
    assert ("Location-Intermediate-4", "Location-Intermediate-5") in name_edges

def test_set_company_attributes(supply_chain_test_data):
    vertices: list[Vertex] = supply_chain_test_data["vertices"]
    routes: list[Route] = supply_chain_test_data["routes"]
    
    locations: list[Location] = supply_chain_test_data["locations"]
    sites: list[Site] = supply_chain_test_data["sites"]
    suppliers: dict[str, Supplier] = supply_chain_test_data["suppliers"]
    manufacturer: Manufacturer = supply_chain_test_data["manufacturer"]
    manufacturer_name = manufacturer.name

    builder = GraphBuilder("db_connection_string")
    builder.graph = ig.Graph(directed=True)

    EPSILON = 0.01
    builder._build_graph_topology(vertices, routes, manufacturer_name)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    builder._resolve_cycles()
    g = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    builder._set_companies_attributes(sites, manufacturer, locations)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    # Site vertex
    site: Site = sites[0]
    site_id: int = site.id
    site_vertex: ig.Vertex = g.vs.find(name=str(site_id))
    
    location: Location = site.location
    m_location: str = manufacturer.location

    assert site_vertex["site_id"] == site.id
    assert site_vertex["company_id"] == site.supplier.id
    assert site_vertex["company_name"] == site.supplier.name
    assert site_vertex["n_rejections"] == site.n_rejections
    assert site_vertex["n_orders"] == site.n_orders
    assert site_vertex["location"] == location.name
    assert abs(site_vertex["receiver_distance"] - GeoCalculator().geodesic_distance(
        location.latitude, location.longitude,
        m_location.latitude, m_location.longitude
    )) < EPSILON
    assert site_vertex["latitude"] == location.latitude
    assert site_vertex["longitude"] == location.longitude

    # Intermediate vertex
    intermediate_location: Location = locations[3] 
    location_name: str = intermediate_location.name
    intermediate_vertex: ig.Vertex = g.vs.find(name=location_name)
    assert intermediate_vertex["location"] == location_name
    assert abs(intermediate_vertex["receiver_distance"] - GeoCalculator().geodesic_distance(
        intermediate_location.latitude, intermediate_location.longitude,
        m_location.latitude, m_location.longitude
    )) < EPSILON
    assert intermediate_vertex["latitude"] == intermediate_location.latitude
    assert intermediate_vertex["longitude"] == intermediate_location.longitude

    # Manufacturer vertex
    manufacturer_name = manufacturer.name
    manufacturer_vertex = g.vs.find(name=manufacturer_name)
    assert manufacturer_vertex["company_id"] == manufacturer.id
    assert manufacturer_vertex["company_name"] == manufacturer.name
    assert manufacturer_vertex["location"] == manufacturer.location.name
    assert manufacturer_vertex["receiver_distance"] == 0.0
    assert manufacturer_vertex["latitude"] == manufacturer.location.latitude
    assert manufacturer_vertex["longitude"] == manufacturer.location.longitude

def test_indicators_explicit_values(supply_chain_test_data):
    vertices: list[Vertex] = supply_chain_test_data["vertices"]
    routes: list[Route] = supply_chain_test_data["routes"]
    
    locations: list[Location] = supply_chain_test_data["locations"]
    sites: list[Site] = supply_chain_test_data["sites"]
    manufacturer: Manufacturer = supply_chain_test_data["manufacturer"]
    manufacturer_name = manufacturer.name

    avg_ori_by_vertex = {v.vertex_id: v.value for v in supply_chain_test_data["avg_ori_per_vertex"]}
    avg_oti_by_route = {(m.source_id, m.destination_id): m.value for m in supply_chain_test_data["avg_oti_per_route"]}
    avg_tmi_by_route = {(m.source_id, m.destination_id): m.value for m in supply_chain_test_data["avg_tmi_per_route"]}
    avg_wmi_by_route = {(m.source_id, m.destination_id): m.value for m in supply_chain_test_data["avg_wmi_per_route"]}

    builder = GraphBuilder("db_connection_string")
    builder.graph = ig.Graph(directed=True)

    EPSILON = 1e-6 

    builder._build_graph_topology(vertices, routes, manufacturer_name)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    builder._resolve_cycles()
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    builder._set_companies_attributes(sites, manufacturer, locations)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    builder._set_indicators_attributes(
        supply_chain_test_data["avg_ori_per_vertex"],
        supply_chain_test_data["avg_oti_per_route"],
        supply_chain_test_data["avg_tmi_per_route"],
        supply_chain_test_data["avg_wmi_per_route"]
    )
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    # Test ORI
    for v in g.vs:
        expected_ori = avg_ori_by_vertex.get(v['v_id'])
        assert expected_ori is not None
        assert abs(v['avg_ori'] - expected_ori) < EPSILON

    # Test OTI, TMI, WMI on routes
    for e in g.es:
        source_id = g.vs[e.source]['v_id']
        source_name = g.vs[e.source]['name']
        dest_id = g.vs[e.target]['v_id']
        dest_name = g.vs[e.target]['name']

        key = (source_id, dest_id)

        # OTI
        expected_oti = avg_oti_by_route.get(key)
        assert expected_oti is not None, f"Missing OTI for route {key}"
        assert abs(e['avg_oti'] - expected_oti) < EPSILON, f"Route {key} OTI expected {expected_oti}, got {e['avg_oti']}"

        # TMI
        expected_tmi = avg_tmi_by_route.get(key)
        assert expected_tmi is not None, f"Missing TMI for route {key}"
        assert abs(e['avg_tmi'] - expected_tmi) < EPSILON, f"Route {key} TMI expected {expected_tmi}, got {e['avg_tmi']}"

        # WMI
        expected_wmi = avg_wmi_by_route.get(key)
        assert expected_wmi is not None, f"Missing WMI for route {key}"
        assert abs(e['avg_wmi'] - expected_wmi) < EPSILON, f"Route {key} WMI expected {expected_wmi}, got {e['avg_wmi']}"

def test_set_orders_attributes(supply_chain_test_data):
    vertices: list[Vertex] = supply_chain_test_data["vertices"]
    routes: list[Route] = supply_chain_test_data["routes"]
    
    locations: list[Location] = supply_chain_test_data["locations"]
    sites: list[Site] = supply_chain_test_data["sites"]
    suppliers: dict[str, Supplier] = supply_chain_test_data["suppliers"]
    manufacturer: Manufacturer = supply_chain_test_data["manufacturer"]
    manufacturer_name = manufacturer.name

    carriers: dict[str, Carrier] = supply_chain_test_data["carriers"]
    n_orders_per_carrier_route: list[CarrierOrderCountResult] = supply_chain_test_data["n_orders_per_carrier_route"]

    order_routes_data: OrderRoutesResult = supply_chain_test_data["order_routes_data"]

    builder = GraphBuilder("db_connection_string")
    builder.graph = ig.Graph(directed=True)

    builder._build_graph_topology(vertices, routes, manufacturer_name)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    builder._resolve_cycles()
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    builder._set_companies_attributes(sites, manufacturer, locations)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    builder._set_indicators_attributes(
        supply_chain_test_data["avg_ori_per_vertex"],
        supply_chain_test_data["avg_oti_per_route"],
        supply_chain_test_data["avg_tmi_per_route"],
        supply_chain_test_data["avg_wmi_per_route"]
    )
    g: ig.Graph = builder.graph
    assert len(g.vs) == 10
    assert len(g.es) == 10

    builder._set_orders_attributes(list(carriers.values()), n_orders_per_carrier_route, order_routes_data)
    assert len(g.vs) == 10
    assert len(g.es) == 10
    g: ig.Graph = builder.graph

    # Check edges have n_orders attribute set correctly
    for edge in g.es:
        assert "n_orders" in edge.attributes(), f"Edge {edge.index} missing 'n_orders' attribute"
        n_orders = edge["n_orders"]
        assert isinstance(n_orders, int), f"Edge {edge.index} n_orders not int"
        assert n_orders > 0, f"Edge {edge.index} n_orders negative"

        assert N_ORDERS_BY_CARRIER_ATTR in edge.attributes(), f"Edge {edge.index} missing 'n_orders_by_carrier' attribute"
        n_orders_by_carrier = edge[N_ORDERS_BY_CARRIER_ATTR]
        assert isinstance(n_orders_by_carrier, dict), f"Edge {edge.index} n_orders_by_carrier not dict"
        for carrier_name in carriers.keys():
            if carrier_name not in n_orders_by_carrier:
                continue
            n_orders_for_carrier = n_orders_by_carrier[carrier_name]
            assert isinstance(n_orders_for_carrier, int), f"Edge {edge.index} n_orders for carrier {carrier_name} not int"
            assert n_orders_for_carrier >= 0, f"Edge {edge.index} n_orders for carrier {carrier_name} negative"

        assert n_orders == sum(n_orders_by_carrier.values()), f"Edge {edge.index} n_orders {n_orders} does not match sum of carriers {sum(n_orders_by_carrier.values())}"
        assert "orders" in  edge.attributes(), f"Edge {edge.index} missing 'orders' attribute"
        orders = edge["orders"]
        assert isinstance(orders, list), f"Edge {edge.index} orders not list"
        for order in orders:
            assert isinstance(order, dict), f"Edge {edge.index} order not dict"
            assert "order_id" in order, f"Edge {edge.index} order missing 'order_id'"
            assert "manufacturer_order_id" in order, f"Edge {edge.index} order missing 'manufacturer_order_id'"
            assert "carrier_name" in order, f"Edge {edge.index} order missing 'carrier_name'"

    # --- FLOW CONSERVATION TEST ---

    for v in g.vs:
        assert v['n_orders'] == sum(v[N_ORDERS_BY_CARRIER_ATTR].values())

        orders = v["orders"]
        assert isinstance(orders, list), f"Vertex {edge.index} orders not list"
        for order in orders:
            assert isinstance(order, dict), f"Vertex {edge.index} order not dict"
            assert "order_id" in order, f"Vertex {edge.index} order missing 'order_id'"
            assert "manufacturer_order_id" in order, f"Vertex {edge.index} order missing 'manufacturer_order_id'"
            assert "carrier_name" in order, f"Vertex {edge.index} order missing 'carrier_name'"
            
        if v[TYPE_ATTR] == VertexType.SUPPLIER_SITE.value:
            incoming_edges = g.incident(v.index, mode="IN")
            outgoing_edges = g.incident(v.index, mode="OUT")
            assert len(incoming_edges) == 0, f"Supplier site {v['v_id']} has incoming edges"
            assert len(outgoing_edges) > 0, f"Supplier site {v['v_id']} has no outgoing edges"

            n_orders = 0
            n_orders_by_carrier = defaultdict(int)
            for e_id in outgoing_edges:
                edge_n_orders = 0
                edge = g.es[e_id]
                for carrier in carriers.keys():
                    carrier_orders = edge[N_ORDERS_BY_CARRIER_ATTR].get(carrier, 0)
                    n_orders_by_carrier[carrier] += carrier_orders
                    edge_n_orders += carrier_orders
                
                assert edge_n_orders == edge["n_orders"], f"Edge {edge.index} n_orders {edge['n_orders']} does not match sum of carriers {edge_n_orders}"
                n_orders += edge_n_orders

            assert n_orders == v["n_orders"], f"Supplier site {v['v_id']} n_orders {v['n_orders']} does not match sum of outgoing edges {n_orders}"
            assert {k: v for (k, v) in n_orders_by_carrier.items() if v > 0} == v[N_ORDERS_BY_CARRIER_ATTR], f"Supplier site {v['v_id']} n_orders_by_carrier {v['n_orders_by_carrier']} does not match sum of outgoing edges {n_orders_by_carrier}"


        elif v[TYPE_ATTR] == VertexType.INTERMEDIATE.value:
            incoming_edges = g.incident(v.index, mode="IN")
            outgoing_edges = g.incident(v.index, mode="OUT")
            assert len(incoming_edges) > 0, f"Intermediate {v['v_id']} has no incoming edges"
            assert len(outgoing_edges) > 0, f"Intermediate {v['v_id']} has no outgoing edges"

            n_orders = 0
            n_orders_by_carrier = defaultdict(int)
            for e_id in incoming_edges:
                incoming_v = g.vs[g.es[e_id].source]
                edge_n_orders = 0
                edge = g.es[e_id]
                for carrier in carriers.keys():
                    carrier_orders = edge[N_ORDERS_BY_CARRIER_ATTR].get(carrier, 0)
                    n_orders_by_carrier[carrier] += carrier_orders
                    edge_n_orders += carrier_orders
                
                assert edge_n_orders == edge["n_orders"], f"Edge {edge.index} n_orders {edge['n_orders']} does not match sum of carriers {edge_n_orders}"
                n_orders += edge_n_orders

            assert n_orders == v["n_orders"], f"Intermediate {v['v_id']} n_orders {v['n_orders']} does not match sum of incoming edges {n_orders}"
            assert {k: v for (k, v) in n_orders_by_carrier.items() if v > 0} == v[N_ORDERS_BY_CARRIER_ATTR], f"Intermediate {v['v_id']} n_orders_by_carrier {v['n_orders_by_carrier']} does not match sum of incoming edges {n_orders_by_carrier}"

            n_orders = 0
            n_orders_by_carrier = defaultdict(int)
            for e_id in outgoing_edges:
                edge_n_orders = 0
                edge = g.es[e_id]
                for carrier in carriers.keys():
                    carrier_orders = edge[N_ORDERS_BY_CARRIER_ATTR].get(carrier, 0)
                    n_orders_by_carrier[carrier] += carrier_orders
                    edge_n_orders += carrier_orders
                
                assert edge_n_orders == edge["n_orders"], f"Edge {edge.index} n_orders {edge['n_orders']} does not match sum of carriers {edge_n_orders}"
                n_orders += edge_n_orders

            assert n_orders == v["n_orders"], f"Intermediate {v['v_id']} n_orders {v['n_orders']} does not match sum of outgoing edges {n_orders}"
            assert {k: v for (k, v) in n_orders_by_carrier.items() if v > 0} == v[N_ORDERS_BY_CARRIER_ATTR], f"Intermediate {v['v_id']} n_orders_by_carrier {v['n_orders_by_carrier']} does not match sum of outgoing edges {n_orders_by_carrier}"


        elif v[TYPE_ATTR] == VertexType.MANUFACTURER.value:
            incoming_edges = g.incident(v.index, mode="IN")
            outgoing_edges = g.incident(v.index, mode="OUT")
            assert len(incoming_edges) > 0, f"Manufacturer {v['v_id']} has no incoming edges"
            assert len(outgoing_edges) == 0, f"Manufacturer {v['v_id']} has outgoing edges"

            n_orders = 0
            n_orders_by_carrier = defaultdict(int)
            for e_id in incoming_edges:
                incoming_v = g.vs[g.es[e_id].source]
                if incoming_v[V_ID_ATTR] == 6:
                    pass
                edge_n_orders = 0
                edge = g.es[e_id]
                for carrier in carriers.keys():
                    carrier_orders = edge[N_ORDERS_BY_CARRIER_ATTR][carrier]
                    n_orders_by_carrier[carrier] += carrier_orders
                    edge_n_orders += carrier_orders
                
                assert edge_n_orders == edge["n_orders"], f"Edge {edge.index} n_orders {edge['n_orders']} does not match sum of carriers {edge_n_orders}"
                n_orders += edge_n_orders

            assert n_orders == v["n_orders"], f"Manufacturer {v['v_id']} n_orders {v['n_orders']} does not match sum of incoming edges {n_orders}"
            assert n_orders_by_carrier == v[N_ORDERS_BY_CARRIER_ATTR], f"Manufacturer {v['v_id']} n_orders_by_carrier {v['n_orders_by_carrier']} does not match sum of incoming edges {n_orders_by_carrier}"



@pytest.fixture(scope="function")
def patch_connector(in_memory_db, seed_data, mocker):
    """
    Monkey‐patch ReadOnlyDBConnector
    """
    class TestConnector(ReadOnlyDBConnector):
        def __init__(self, _: str):
            self._SessionLocal = lambda: in_memory_db

        @contextmanager
        def session_scope(self):
            session = self._SessionLocal()
            try:
                yield session
            finally:
                session.close()

    mocker.patch("builder_service.graph_builder.ReadOnlyDBConnector", new=TestConnector)

def test_build_graph(patch_connector):
    builder: GraphBuilder = GraphBuilder("dummy_connection_string")

    graph: ig.Graph = builder.build()

    assert isinstance(graph, ig.Graph)
    assert graph.is_directed()
    assert graph.is_connected(mode='weak')      # Weakly connected for directed graphs
    assert graph.is_simple()                    # No self-loops or multiple edges
    assert graph.is_dag()                       # Directed acyclic graph

    assert len(graph.vs) == 5  # 2 sites, 2 intermediates, 1 manufacturer
    assert len(graph.es) == 5  # 5 routes
    
    sites_v = graph.vs.select(type=VertexType.SUPPLIER_SITE.value)
    assert len(sites_v) == 2
    for v in sites_v:
        assert graph.degree(v.index, mode="IN") == 0
        assert graph.degree(v.index, mode="OUT") > 0

    intermediates_v = graph.vs.select(type=VertexType.INTERMEDIATE.value)
    assert len(intermediates_v) == 2
    for v in intermediates_v:
        assert graph.degree(v.index, mode="IN") > 0
        assert graph.degree(v.index, mode="OUT") > 0

    manufacturer_v = graph.vs.select(type=VertexType.MANUFACTURER.value)
    assert len(manufacturer_v) == 1
    for v in manufacturer_v:
        assert graph.degree(v.index, mode="IN") > 0
        assert graph.degree(v.index, mode="OUT") == 0



@pytest.fixture(scope="module")
def test_empty_data():
    # Locations - one per vertex
    locations = {}

    # Carriers
    carriers = {}

    # Suppliers for each supplier vertex
    suppliers = {
    }

    # Sites for each supplier
    sites = []

    # Manufacturer object with location
    manufacturer = Manufacturer()

    # Vertices
    vertices = []

    # Routes
    routes = []

    n_orders_per_carrier_route = []

    order_routes_data = []

    # Explicitly define ORI per vertex: (vertex_id, avg_ori)
    avg_ori_per_vertex = []

    # Explicitly define OTI per route: (source_id, dest_id, avg_oti)
    avg_oti_per_route = []

    # Explicitly define TMI per route: (source_id, dest_id, avg_tmi)
    avg_tmi_per_route = []

    # Explicitly define WMI per route: (source_id, dest_id, avg_wmi)
    avg_wmi_per_route = []

    # Extend the return dict with the indicators
    return {
        "vertices": vertices,
        "routes": routes,
        "n_orders_per_carrier_route": n_orders_per_carrier_route,
        "order_routes_data": order_routes_data,
        "sites": sites,
        "suppliers": suppliers,
        "manufacturer": manufacturer,
        "carriers": carriers,
        "locations": list(locations.values()),
        "avg_ori_per_vertex": avg_ori_per_vertex,
        "avg_oti_per_route": avg_oti_per_route,
        "avg_tmi_per_route": avg_tmi_per_route,
        "avg_wmi_per_route": avg_wmi_per_route,
    }


def test_build_graph_topology_empty_db(test_empty_data):
    vertices: list[Vertex] = test_empty_data["vertices"]
    routes: list[Route] = test_empty_data["routes"]

    manufacturer: Manufacturer = test_empty_data["manufacturer"]
    manufacturer_name = manufacturer.name

    builder = GraphBuilder("db_connection_string")
    builder.graph = ig.Graph(directed=True)
    builder._build_graph_topology(vertices, routes, manufacturer_name)
    g: ig.Graph = builder.graph

    assert len(g.vs) == 0
    assert len(g.es) == 0

def test_set_company_attributes_empty_db(test_empty_data):
    vertices: list[Vertex] = test_empty_data["vertices"]
    routes: list[Route] = test_empty_data["routes"]
    
    locations: list[Location] = test_empty_data["locations"]
    sites: list[Site] = test_empty_data["sites"]
    manufacturer: Manufacturer = test_empty_data["manufacturer"]
    manufacturer_name = manufacturer.name

    builder = GraphBuilder("db_connection_string")
    builder.graph = ig.Graph(directed=True)

    EPSILON = 0.01
    builder._build_graph_topology(vertices, routes, manufacturer_name)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 00

    builder._resolve_cycles()
    g = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

    builder._set_companies_attributes(sites, manufacturer, locations)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

def test_indicators_explicit_values_empty_db(test_empty_data):
    vertices: list[Vertex] = test_empty_data["vertices"]
    routes: list[Route] = test_empty_data["routes"]
    
    locations: list[Location] = test_empty_data["locations"]
    sites: list[Site] = test_empty_data["sites"]
    manufacturer: Manufacturer = test_empty_data["manufacturer"]
    manufacturer_name = manufacturer.name

    builder = GraphBuilder("db_connection_string")
    builder.graph = ig.Graph(directed=True)

    builder._build_graph_topology(vertices, routes, manufacturer_name)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

    builder._resolve_cycles()
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

    builder._set_companies_attributes(sites, manufacturer, locations)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

    builder._set_indicators_attributes(
        test_empty_data["avg_ori_per_vertex"],
        test_empty_data["avg_oti_per_route"],
        test_empty_data["avg_tmi_per_route"],
        test_empty_data["avg_wmi_per_route"]
    )
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

def test_set_orders_attributes_empty_db(test_empty_data):
    vertices: list[Vertex] = test_empty_data["vertices"]
    routes: list[Route] = test_empty_data["routes"]
    
    locations: list[Location] = test_empty_data["locations"]
    sites: list[Site] = test_empty_data["sites"]
    suppliers: dict[str, Supplier] = test_empty_data["suppliers"]
    manufacturer: Manufacturer = test_empty_data["manufacturer"]
    manufacturer_name = manufacturer.name

    carriers: dict[str, Carrier] = test_empty_data["carriers"]
    n_orders_per_carrier_route: list[tuple[int, int, str, int]] = test_empty_data["n_orders_per_carrier_route"]
    order_routes_data = test_empty_data["order_routes_data"]

    builder = GraphBuilder("db_connection_string")
    builder.graph = ig.Graph(directed=True)

    builder._build_graph_topology(vertices, routes, manufacturer_name)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

    builder._resolve_cycles()
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

    builder._set_companies_attributes(sites, manufacturer, locations)
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

    builder._set_indicators_attributes(
        test_empty_data["avg_ori_per_vertex"],
        test_empty_data["avg_oti_per_route"],
        test_empty_data["avg_tmi_per_route"],
        test_empty_data["avg_wmi_per_route"]
    )
    g: ig.Graph = builder.graph
    assert len(g.vs) == 0
    assert len(g.es) == 0

    builder._set_orders_attributes(list(carriers.values()), n_orders_per_carrier_route, order_routes_data)
    assert len(g.vs) == 0
    assert len(g.es) == 0
    

@pytest.fixture(scope="function")
def patch_connector_empty_db(in_memory_db, mocker):
    """
    Monkey‐patch ReadOnlyDBConnector
    """
    class TestConnector(ReadOnlyDBConnector):
        def __init__(self, _: str):
            self._SessionLocal = lambda: in_memory_db

        @contextmanager
        def session_scope(self):
            session = self._SessionLocal()
            try:
                yield session
            finally:
                session.close()

    mocker.patch("builder_service.graph_builder.ReadOnlyDBConnector", new=TestConnector)

def test_build_graph_empty_db(patch_connector_empty_db):
    builder: GraphBuilder = GraphBuilder("dummy_connection_string")

    graph: ig.Graph = builder.build()
    assert len(graph.vs) == 0
    assert len(graph.es) == 0