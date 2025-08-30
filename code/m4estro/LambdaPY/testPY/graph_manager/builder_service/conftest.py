import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model.vertex import Vertex, VertexType
from model.route import Route
from model.site import Site
from model.country import Country
from model.base import Base
from model.supplier import Supplier
from model.carrier import Carrier
from model.order import Order, OrderStatus
from model.manufacturer import Manufacturer
from model.location import Location
from model.ori import ORI
from model.oti import OTI
from model.tmi import TMI, TransportationMode
from model.wmi import WMI
from model.route_order import RouteOrder


@pytest.fixture(scope="function")
def in_memory_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()

@pytest.fixture(scope="function")
def seed_data(in_memory_db):
    """
    Seed the in-memory database with countries, locations, suppliers, carriers,
    sites, and delivery-time (gamma & sample) records.
    """
    session = in_memory_db

    # --- Countries ---
    country = Country(code="IT", name="Italy", total_holidays=10, weekend_start=6, weekend_end=7)
    session.add(country)
    session.commit()

    # --- Locations ---
    locations = [
        Location(name="Location A", city="A", state="AA", country_code="IT", latitude=0.0, longitude=0.0),
        Location(name="Location B", city="B", state="BB", country_code="IT", latitude=1.0, longitude=1.0),
        Location(name="Location C", city="C", state="CC", country_code="IT", latitude=2.0, longitude=2.0),
        Location(name="Location D", city="D", state="DD", country_code="IT", latitude=3.0, longitude=3.0),
        Location(name="Location E", city="E", state="EE", country_code="IT", latitude=4.0, longitude=4.0),
        Location(name="Location F", city="F", state="FF", country_code="IT", latitude=5.0, longitude=5.0),
    ]
    session.add_all(locations)
    session.commit()

    # --- Suppliers ---
    supplier1 = Supplier(id=10, manufacturer_supplier_id=100, name="Supplier A")
    session.add_all([supplier1])
    session.commit()

    # --- Manufacturer ---
    manufacturer = Manufacturer(id=1, name="Manu", location_name="Location F")
    session.add(manufacturer)

    # --- Carriers ---
    dhl = Carrier(id=1, name="dhl", carrier_17track_id="10000")
    fedex = Carrier(id=2, name="fedex", carrier_17track_id="20000")
    session.add_all([dhl, fedex])
    session.commit()

    # --- Sites ---
    site1 = Site(id=1, supplier_id=10, location_name="Location A", n_rejections=5, n_orders=2)
    site2 = Site(id=2, supplier_id=10, location_name="Location B", n_rejections=3, n_orders=1)
    session.add_all([site1, site2])
    session.commit()

    # --- Orders ---
    orders = [
        Order(id=1, manufacturer_id=manufacturer.id, manufacturer_order_id=101, site_id=1, carrier=dhl, status=OrderStatus.DELIVERED.value, n_steps=3, tracking_link=None, tracking_number="100", manufacturer_creation_timestamp=datetime(2025, 6, 1, 9, 0, 0), SLS=False),
        Order(id=2, manufacturer_id=manufacturer.id, manufacturer_order_id=102, site_id=1, carrier=fedex, status=OrderStatus.DELIVERED.value, n_steps=4, tracking_link=None, tracking_number="101", manufacturer_creation_timestamp=datetime(2025, 6, 2, 10, 0, 0), SLS=False),
        Order(id=3, manufacturer_id=manufacturer.id, manufacturer_order_id=103, site_id=2, carrier=dhl, status=OrderStatus.DELIVERED.value, n_steps=5, tracking_link=None, tracking_number="102", manufacturer_creation_timestamp=datetime(2025, 6, 3, 11, 0, 0), SLS=False),
    ]
    session.add_all(orders)
    session.commit()

    # --- Vertices ---
    vertices = [
        Vertex(id=1, name="1", type=VertexType.SUPPLIER_SITE),
        Vertex(id=2, name="2", type=VertexType.SUPPLIER_SITE),
        Vertex(id=3, name="Location C", type=VertexType.INTERMEDIATE),
        Vertex(id=4, name="Location D", type=VertexType.INTERMEDIATE),
        Vertex(id=5, name="1", type=VertexType.MANUFACTURER),
    ]
    session.add_all(vertices)
    session.commit()

    # --- Routes ---
    routes = [
        Route(id=1, source_id=1, destination_id=3),
        Route(id=3, source_id=3, destination_id=5),
        Route(id=2, source_id=3, destination_id=4),
    
        Route(id=5, source_id=2, destination_id=4),

        Route(id=4, source_id=4, destination_id=5),

    ]
    session.add_all(routes)
    session.commit()

    # --- RouteOrders ---
    route_orders = [
        RouteOrder(id=1, order_id=1, source_id=1, destination_id=3),
        RouteOrder(id=2, order_id=1, source_id=3, destination_id=5),

        RouteOrder(id=3, order_id=2, source_id=1, destination_id=3),
        RouteOrder(id=4, order_id=2, source_id=3, destination_id=4),
        RouteOrder(id=5, order_id=2, source_id=4, destination_id=5),

        RouteOrder(id=6, order_id=3, source_id=2, destination_id=4),
    ]
    session.add_all(route_orders)
    session.commit()

    # Example ORI for vertices
    ori_records = [
        ORI(vertex_id=1, created_at=datetime(2025, 6, 1, 9, 0, 0), hours=0.8),
        ORI(vertex_id=2, created_at=datetime(2025, 6, 2, 10, 0, 0), hours=0.85),
        ORI(vertex_id=3, created_at=datetime(2025, 6, 3, 11, 0, 0), hours=0.9),
        ORI(vertex_id=4, created_at=datetime(2025, 6, 4, 12, 0, 0), hours=0.75),
        ORI(vertex_id=5, created_at=datetime(2025, 6, 5, 13, 0, 0), hours=0.95),
    ]
    session.add_all(ori_records)
    session.commit()

    # Example OTI for routes
    oti_records = [
        OTI(source_id=1, destination_id=3, created_at=datetime(2025, 6, 1, 9, 0, 0), hours=2.0),
        OTI(source_id=3, destination_id=5, created_at=datetime(2025, 6, 2, 10, 0, 0), hours=4.0),
        OTI(source_id=3, destination_id=4, created_at=datetime(2025, 6, 3, 11, 0, 0), hours=3.0),

        OTI(source_id=2, destination_id=4, created_at=datetime(2025, 6, 4, 12, 0, 0), hours=1.5),
        OTI(source_id=4, destination_id=5, created_at=datetime(2025, 6, 5, 13, 0, 0), hours=2.5),
    ]
    session.add_all(oti_records)
    session.commit()

    # Example TMI (transit mean indicator) for routes
    tmi_records = [
        TMI(source_id=1, destination_id=3, created_at=datetime(2025, 6, 1, 9, 0, 0), timestamp=datetime(2025, 6, 1, 9, 0, 0), transportation_mode=TransportationMode.ROAD, value=0.1),
        TMI(source_id=3, destination_id=5, created_at=datetime(2025, 6, 2, 10, 0, 0), timestamp=datetime(2025, 6, 2, 10, 0, 0), transportation_mode=TransportationMode.RAIL, value=0.2),
        TMI(source_id=3, destination_id=4, created_at=datetime(2025, 6, 3, 11, 0, 0), timestamp=datetime(2025, 6, 3, 11, 0, 0), transportation_mode=TransportationMode.ROAD, value=0.44),

        TMI(source_id=2, destination_id=4, created_at=datetime(2025, 6, 4, 12, 0, 0), timestamp=datetime(2025, 6, 4, 12, 0, 0), transportation_mode=TransportationMode.SEA, value=0.15),

        TMI(source_id=4, destination_id=5, created_at=datetime(2025, 6, 5, 13, 0, 0), timestamp=datetime(2025, 6, 5, 13, 0, 0), transportation_mode=TransportationMode.AIR, value=0.2),
    ]
    session.add_all(tmi_records)
    session.commit()

    # Example WMI (weight mean indicator) for routes
    wmi_records = [
        WMI(source_id=1, destination_id=3, created_at=datetime(2025, 6, 1, 9, 0, 0), timestamp=datetime(2025, 6, 1, 9, 0, 0), n_interpolation_points=10, step_distance_km=100.0, value=0.3),
        WMI(source_id=3, destination_id=5, created_at=datetime(2025, 6, 2, 10, 0, 0), timestamp=datetime(2025, 6, 2, 10, 0, 0), n_interpolation_points=15, step_distance_km=150.0, value=0.5),
        WMI(source_id=3, destination_id=4, created_at=datetime(2025, 6, 3, 11, 0, 0), timestamp=datetime(2025, 6, 3, 11, 0, 0), n_interpolation_points=12, step_distance_km=120.0, value=0.44),

        WMI(source_id=2, destination_id=4, created_at=datetime(2025, 6, 4, 12, 0, 0), timestamp=datetime(2025, 6, 4, 12, 0, 0), n_interpolation_points=8, step_distance_km=80.0, value=0.35),

        WMI(source_id=4, destination_id=5, created_at=datetime(2025, 6, 5, 13, 0, 0), timestamp=datetime(2025, 6, 5, 13, 0, 0), n_interpolation_points=20, step_distance_km=200.0, value=0.45),
    ]
    session.add_all(wmi_records)
    session.commit()