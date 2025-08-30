import pytest
from typing import List

from builder_service.query_handler import QueryHandler
from builder_service.query_handler import (
    AvgVertexMetricResult,
    AvgRouteMetricResult,
    CarrierOrderCountResult,
    OrderRoutesResult,
)
from model.vertex import VertexType

class TestQueryHandler:
    
    def test_get_manufacturer(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        manu = qh.get_manufacturer()
        assert manu is not None
        assert manu.name == "Manu"
        assert manu.location_name == "Location F"

    def test_get_all_vertices(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        vertices = qh.get_all_vertices()
        assert len(vertices) == 5
        names = {v.name for v in vertices}
        assert "1" in names
        assert "Location C" in names
        assert any(v.type == VertexType.SUPPLIER_SITE for v in vertices)
        assert any(v.type == VertexType.MANUFACTURER for v in vertices)

    def test_get_all_routes(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        routes = qh.get_all_routes()
        assert len(routes) == 5
        source_ids = {r.source_id for r in routes}
        destination_ids = {r.destination_id for r in routes}
        assert 1 in source_ids
        assert 3 in destination_ids

    def test_get_all_locations(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        locations = qh.get_all_locations()
        assert len(locations) == 6
        city_names = {loc.city for loc in locations}
        assert "A" in city_names
        assert "F" in city_names

    def test_get_all_sites(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        sites = qh.get_all_sites()
        assert len(sites) == 2
        supplier_ids = {site.supplier_id for site in sites}
        assert 10 in supplier_ids
        assert any(site.location_name == "Location A" or (site.location and site.location.name == "Location B") for site in sites)

    def test_get_all_carriers(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        carriers = qh.get_all_carriers()
        carrier_names = {c.name for c in carriers}
        assert "dhl" in carrier_names
        assert "fedex" in carrier_names

    def test_get_avg_ori_per_vertex(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        avg_oris: List[AvgVertexMetricResult] = qh.get_avg_ori_per_vertex()
        assert len(avg_oris) == 5
        v1_ori = next((v.value for v in avg_oris if v.vertex_id == 1), None)
        assert v1_ori is not None
        assert abs(v1_ori - 0.8) < 1e-6

    def test_get_avg_oti_per_route(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        avg_otis: List[AvgRouteMetricResult] = qh.get_avg_oti_per_route()
        assert len(avg_otis) == 5
        route = next((r for r in avg_otis if r.source_id == 1 and r.destination_id == 3), None)
        assert route is not None
        assert abs(route.value - 2.0) < 1e-6

    def test_get_avg_tmi_per_route(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        avg_tmis: List[AvgRouteMetricResult] = qh.get_avg_tmi_per_route()
        assert len(avg_tmis) == 5
        route = next((r for r in avg_tmis if r.source_id == 3 and r.destination_id == 4), None)
        assert route is not None
        assert abs(route.value - 0.44) < 1e-6

    def test_get_avg_wmi_per_route(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        avg_wmis: List[AvgRouteMetricResult] = qh.get_avg_wmi_per_route()
        assert len(avg_wmis) == 5
        route = next((r for r in avg_wmis if r.source_id == 3 and r.destination_id == 5), None)
        assert route is not None
        assert abs(route.value - 0.5) < 1e-6

    def test_n_orders_per_carrier_route(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        results: List[CarrierOrderCountResult] = qh.get_n_orders_per_carrier_route()
        assert results
        found = False
        for r in results:
            if r.source_id == 1 and r.destination_id == 3 and r.carrier_id == 1:
                assert r.route_carrier_orders_count == 1
                found = True
        assert found

    def test_get_order_routes(self, seed_data, in_memory_db):
        qh = QueryHandler(in_memory_db)
        order_routes: List[OrderRoutesResult] = qh.get_order_routes()
        assert len(order_routes) == 6
        found = any(
            r.source_id == 1 and r.destination_id == 3 and r.order_id == 1 and r.manufacturer_order_id == 101
            for r in order_routes
        )
        assert found
        for r in order_routes:
            assert isinstance(r.source_id, int)
            assert isinstance(r.destination_id, int)
            assert isinstance(r.order_id, int)
            assert isinstance(r.manufacturer_order_id, int)
            assert isinstance(r.tracking_number, str)
            assert isinstance(r.carrier_id, int)
