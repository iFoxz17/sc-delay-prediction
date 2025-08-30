import pytest
import igraph as ig

from model.vertex import VertexType

from graph_config import (
    V_ID_ATTR,
    TYPE_ATTR,
    N_ORDERS_BY_CARRIER_ATTR,
)

from exporter_service.graph_exporter import GraphExporter

@pytest.fixture
def simple_graph():
    g = ig.Graph(directed=True)

    # Add one vertex
    g.add_vertex(
        v_id=1,
        name="S1",
        type="SUPPLIER_SITE",
        location="Berlin",
        receiver_distance=42.0,
        latitude=52.52,
        longitude=13.4050,
        site_id=100,
        company_id=200,
        company_name="ACME",
        manufacturer_supplier_id=300,
        orders=[
            {"order_id": 1, "manufacturer_order_id": 10, "tracking_number": "1000", "carrier_name": "DHL"}
        ],
        **{
            N_ORDERS_BY_CARRIER_ATTR: {"DHL": 1, "UPS": 0},
        },
        n_orders=1,
        n_rejections=0,
        avg_ori=2.5
    )

    # Add a second vertex
    g.add_vertex(
        v_id=2,
        name="M1",
        type="MANUFACTURER",
        location="Munich",
        receiver_distance=84.0,
        latitude=48.1351,
        longitude=11.5820,
        site_id=None,
        company_id=None,
        company_name=None,
        manufacturer_supplier_id=None,
        orders=[
            {"order_id": 1, "manufacturer_order_id": 10, "tracking_number": "1000", "carrier_name": "DHL"}
        ],
        **{
            N_ORDERS_BY_CARRIER_ATTR: {"DHL": 0, "UPS": 0},
        },
        n_orders=0,
        n_rejections=None,
        avg_ori=None
    )

    # Add an edge between the two
    g.add_edge(
        source=0,
        target=1,
        orders=[
            {"order_id": 1, "manufacturer_order_id": 10, "tracking_number": "1000", "carrier_name": "DHL"}
        ],
        **{
            N_ORDERS_BY_CARRIER_ATTR: {"DHL": 1, "UPS": 0}
        },
        n_orders=1,
        distance=500.0,
        avg_oti=3.1,
        avg_wmi=2.7,
        avg_tmi=1.8
    )

    return g


def test_export_as_graph(simple_graph):
    exporter = GraphExporter()
    result = exporter.export_as_graph(simple_graph)

    assert isinstance(result, dict)
    assert "nodes" in result
    assert "links" in result
    assert len(result["nodes"]) == 2
    assert len(result["links"]) == 1

    node = result["nodes"][0]
    assert node[V_ID_ATTR] == 1
    assert node["name"] == "S1"
    assert node[TYPE_ATTR] == VertexType.SUPPLIER_SITE.value
    assert node["location"] == "Berlin"
    assert node["receiver_distance"] == 42.0
    assert node["coordinates"] == [52.52, 13.4050]
    assert node["site_id"] == 100
    assert node["company_id"] == 200
    assert node["company_name"] == "ACME"
    assert node["manufacturer_supplier_id"] == 300
    assert isinstance(node["packages"], list)
    assert len(node["packages"]) == 1
    assert node["packages"][0]["order_id"] == 1
    assert node["packages"][0]["manufacturer_order_id"] == 10
    assert node["packages"][0]["tracking_number"] == "1000"
    assert node["packages"][0]["carrier_name"] == "DHL"
    assert node["n_orders_by_carrier"] == {"DHL": 1, "UPS": 0}
    assert node["n_orders"] == 1
    assert node["n_rejections"] == 0
    assert node["avg_ORI"] == 2.5

    link = result["links"][0]
    assert link["source"] == 1  # source v_id
    assert link["target"] == 2  # target v_id
    assert link["packages"] == [{"order_id": 1, "manufacturer_order_id": 10, "tracking_number": "1000", "carrier_name": "DHL"}]
    assert link["n_orders_by_carrier"] == {"DHL": 1, "UPS": 0}
    assert link["n_orders"] == 1
    assert link["distance"] == 500.0
    assert link["avg_OTI"] == 3.1
    assert link["avg_WMI"] == 2.7
    assert link["avg_TMI"] == 1.8

def test_export_as_map(simple_graph):

    exporter = GraphExporter()
    result = exporter.export_as_map(simple_graph)

    assert "nodes" in result
    assert "links" in result
    assert len(result["nodes"]) == 2
    assert len(result["links"]) == 1

    node = next(n for n in result["nodes"] if n[TYPE_ATTR] == VertexType.SUPPLIER_SITE.value)
    assert node[V_ID_ATTR] == 1
    assert node["name"] == "S1"
    assert node["coordinates"] == [52.52, 13.4050]
    assert node["company_id"] == 200
    assert node["packages"] == [{"order_id": 1, "manufacturer_order_id": 10, "tracking_number": "1000", "carrier_name": "DHL"}]
    assert node["n_orders_by_carrier"] == {"DHL": 1, "UPS": 0}
    assert node["n_orders"] == 1
    assert node["n_rejections"] == 0

    manufacturer = next(n for n in result["nodes"] if n[TYPE_ATTR] == VertexType.MANUFACTURER.value)
    assert manufacturer[V_ID_ATTR] == 2
    assert manufacturer["site_id"] is None
    assert manufacturer["manufacturer_supplier_id"] is None

    link = result["links"][0]
    assert link["source"] == 1
    assert link["target"] == 2
    assert link["packages"] == [{"order_id": 1, "manufacturer_order_id": 10, "tracking_number": "1000", "carrier_name": "DHL"}]
    assert link["n_orders_by_carrier"] == {"DHL": 1, "UPS": 0}
    assert link["n_orders"] == 1
    assert "distance" in link
    assert link["distance"] > 400