import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
import sqlite3

from model.base import Base

from model.country import Country
from model.location import Location
from model.holiday import Holiday, HolidayCategory
from model.supplier import Supplier
from model.manufacturer import Manufacturer
from model.carrier import Carrier
from model.site import Site 
from model.order import Order
from model.order_step import OrderStep
from model.dispatch_time import DispatchTime
from model.dispatch_time_gamma import DispatchTimeGamma
from model.dispatch_time_sample import DispatchTimeSample
from model.shipment_time import ShipmentTime
from model.shipment_time_gamma import ShipmentTimeGamma
from model.shipment_time_sample import ShipmentTimeSample
from model.vertex import Vertex, VertexType
from model.route import Route
from model.route_order import RouteOrder
from model.oti import OTI
from model.ori import ORI
from model.estimated_time import EstimatedTime
from model.estimated_time_holiday import EstimatedTimeHoliday
from model.time_deviation import TimeDeviation
from model.estimation_params import EstimationParams
from model.wmi import WMI
from model.tmi import TMI, TransportationMode
from model.order_step_enriched import OrderStepEnriched
from model.weather_data import WeatherData
from model.alpha import Alpha, AlphaType
from model.alpha_opt import AlphaOpt
from model.param import Param
from model.time_deviation import TimeDeviation

@pytest.fixture(scope="function")
def engine():
    # In-memory SQLite DB for testing
    sqlite3.register_adapter(datetime, lambda val: val.isoformat())  # e.g., '2025-06-26T12:00:00'

    # Register converters
    sqlite3.register_converter("timestamp", lambda val: datetime.fromisoformat(val.decode("utf-8")))

    # Example SQLAlchemy engine with type detection enabled
    from sqlalchemy import create_engine

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"detect_types": sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES}
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="function")
def session(engine):
    """Creates a new session for a test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_country(session):
    country = Country(
        code="US",
        name="United States",
        total_holidays=10,
        weekend_start=6,  # Saturday
        weekend_end=7     # Sunday
    )
    session.add(country)
    session.commit()

    # Retrieve from DB
    result = session.query(Country).filter_by(code="US").first()

    assert result is not None
    assert result.code == "US"
    assert result.name == "United States"
    assert result.total_holidays == 10
    assert result.weekend_start == 6
    assert result.weekend_end == 7

def test_create_location(session):
    country = Country(
        code="IT",
        name="Italy",
        total_holidays=12,
        weekend_start=6,
        weekend_end=7
    )
    session.add(country)
    session.commit()

    location = Location(
        name="Rome, Lazio, Italy",
        city="Rome",
        state="Lazio",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    session.add(location)
    session.commit()

    # Fetch and verify
    result = session.query(Location).filter_by(name="Rome, Lazio, Italy").first()
    assert result is not None
    assert result.name == "Rome, Lazio, Italy"
    assert result.city == "Rome"
    assert result.state == "Lazio"
    assert result.country_code == "IT"
    assert result.latitude == 41.9028
    assert result.longitude == 12.4964
    assert result.country.name == "Italy"  # Check relationship is populated

def test_create_and_query_holiday(session):
    # Add a country first
    italy = Country(
        code="IT",
        name="Italy",
        total_holidays=15,
        weekend_start=6,
        weekend_end=7
    )
    session.add(italy)
    session.commit()

    # Add a holiday
    holiday = Holiday(
        name="Ferragosto",
        country_code="IT",
        category=HolidayCategory.CLOSURE,
        description="Public summer holiday",
        url="https://example.com/ferragosto",
        type="Public",
        date=datetime(2023, 8, 15, tzinfo=timezone.utc),  # Ferragosto is on August 15
        week_day=5,    # Friday
        month=8,
        year_day=227
    )
    session.add(holiday)
    session.commit()

    # Retrieve and check
    fetched = session.query(Holiday).filter_by(name="Ferragosto").first()
    assert fetched is not None
    assert fetched.country_code == "IT"
    assert fetched.country.name == "Italy"
    assert fetched.category == HolidayCategory.CLOSURE
    assert fetched.description == "Public summer holiday"
    assert fetched.url.startswith("https://")

def test_create_supplier(session):
    # Create a supplier
    supplier = Supplier(manufacturer_supplier_id=100, name="Test Supplier")
    session.add(supplier)
    session.commit()

    # Fetch from DB
    result = session.query(Supplier).filter_by(name="Test Supplier").first()
    assert result is not None
    assert result.name == "Test Supplier"

def test_create_site(session):
    # Setup: Create country and location
    country = Country(
        code="US",
        name="United States",
        total_holidays=10,
        weekend_start=6,
        weekend_end=7
    )
    session.add(country)

    location = Location(
        name="New York",
        city="New York",
        state="NY",
        country_code="US",
        latitude=40.7128,
        longitude=-74.0060
    )
    session.add(location)
    session.flush()

    # Create supplier and first site
    supplier = Supplier(manufacturer_supplier_id=100, name="Supplier A")
    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=2,
        n_orders=10
    )
    session.add(site)
    session.commit()

    # Check site was added correctly
    assert len(supplier.sites) == 1
    assert supplier.sites[0].location.name == "New York"
    assert site.supplier.name == "Supplier A"

    # Attempt to add a second site with same (supplier, location)
    duplicate_site = Site(
        supplier=supplier,
        location=location,
        n_rejections=0,
        n_orders=1
    )
    session.add(duplicate_site)

    with pytest.raises(IntegrityError):
        session.commit()

def test_create_manufacturer(session):
    # Add required foreign key dependency
    country = Country(
        code="DE",
        name="Germany",
        total_holidays=9,
        weekend_start=6,
        weekend_end=7
    )
    session.add(country)

    location = Location(
        name="Berlin",
        city="Berlin",
        state="BE",
        country_code="DE",
        latitude=52.52,
        longitude=13.4050
    )
    session.add(location)
    session.commit()

    # Create Manufacturer
    manufacturer = Manufacturer(
        name="Bosch",
        location_name="Berlin"
    )
    session.add(manufacturer)
    session.commit()

    # Fetch and assert
    result = session.query(Manufacturer).filter_by(name="Bosch").first()
    assert result is not None
    assert result.name == "Bosch"
    assert result.location.name == "Berlin"
    assert result.location.city == "Berlin"

def test_create_carrier(session):
    # Create Carrier with explicit losses and delays
    carrier1 = Carrier(name="Carrier One", carrier_17track_id="1000", n_losses=5, n_orders=8)
    session.add(carrier1)
    session.commit()

    c1 = session.query(Carrier).filter_by(name="Carrier One").first()
    assert c1 is not None
    assert c1.name == "Carrier One"
    assert c1.carrier_17track_id == "1000"
    assert c1.n_losses == 5
    assert c1.n_orders == 8

    # Create Carrier with defaults (no losses or delays provided)
    carrier2 = Carrier(name="Carrier Two", carrier_17track_id="2000")
    session.add(carrier2)
    session.commit()

    carrier2.n_losses += 1
    carrier2.n_orders += 1
    session.commit()

    c2 = session.query(Carrier).filter_by(name="Carrier Two").first()
    assert c2 is not None
    assert c2.n_losses == 1  # default
    assert c2.n_orders == 1  # default

def test_create_order(session):
    # Set up foreign key dependencies
    country = Country(
        code="FR",
        name="France",
        total_holidays=11,
        weekend_start=6,
        weekend_end=7
    )
    session.add(country)

    location = Location(
        name="Paris, IDF, France",
        city="Paris",
        state="IDF",
        country_code="FR",
        latitude=48.8566,
        longitude=2.3522
    )
    session.add(location)

    carrier = Carrier(
        name="LaPoste",
        carrier_17track_id="1234",
        n_losses=1,
        n_orders=2
    )
    session.add(carrier)

    manufacturer = Manufacturer(
        name="Renault",
        location_name="Paris"
    )
    session.add(manufacturer)
    
    supplier = Supplier(manufacturer_supplier_id=100, name="Renault Supplier")
    session.add(supplier)
    session.commit()    

    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=0,
        n_orders=0,
    )

    session.add(site)
    session.commit()

    # Create the order
    order = Order(
        manufacturer_id=manufacturer.id,
        manufacturer_order_id=1001,
        site_id=site.id,
        carrier=carrier,
        status="CREATED",
        n_steps=3,
        tracking_link="http://track.me/123",
        tracking_number="123",
        manufacturer_creation_timestamp=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        manufacturer_estimated_delivery_timestamp=datetime(2025, 6, 10, 12, 0, 0, tzinfo=timezone.utc),
        manufacturer_confirmed_delivery_timestamp=None,
        carrier_creation_timestamp=datetime(2025, 6, 2, 8, 0, 0, tzinfo=timezone.utc),
        carrier_estimated_delivery_timestamp=datetime(2025, 6, 9, 18, 0, 0, tzinfo=timezone.utc),
        carrier_confirmed_delivery_timestamp=None,
        SLS=True
    )
    session.add(order)
    session.commit()

    result = session.query(Order).filter_by(manufacturer_order_id=1001).first()
    assert result is not None
    assert result.manufacturer.name == "Renault"
    assert result.carrier.name == "LaPoste"
    assert result.status == "CREATED"
    assert result.SLS is True

def test_create_order_step(session):
    # Set up dependencies
    country = Country(code="IT", name="Italy", total_holidays=12, weekend_start=6, weekend_end=7)
    location = Location(
        name="Rome",
        city="Rome",
        state="RM",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    carrier = Carrier(name="PosteItaliane", carrier_17track_id="1234", n_losses=0, n_orders=0)
    manufacturer = Manufacturer(name="Fiat", location_name="Rome")
    supplier = Supplier(manufacturer_supplier_id=100, name="Fiat Supplier")
    site = Site(supplier=supplier, location=location, n_rejections=0, n_orders=0)

    session.add_all([country, location, carrier, manufacturer, site])
    session.flush()

    # Create a minimal order
    order = Order(
        manufacturer_id=manufacturer.id,
        manufacturer_order_id=101,
        site_id=site.id,
        carrier=carrier,
        status="PROCESSING",
        n_steps=2,
        tracking_link=None,
        tracking_number="123",
        manufacturer_creation_timestamp=datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
        manufacturer_estimated_delivery_timestamp=None,
        manufacturer_confirmed_delivery_timestamp=None,
        carrier_creation_timestamp=None,
        carrier_estimated_delivery_timestamp=None,
        carrier_confirmed_delivery_timestamp=None,
        SLS=False
    )
    session.add(order)
    session.flush()

    # Create OrderStep
    step = OrderStep(
        order_id=order.id,
        step=1,
        status="CREATED",
        timestamp=datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
        location="Rome"
    )
    session.add(step)
    session.commit()

    result = session.query(OrderStep).filter_by(order_id=order.id, step=1).first()
    assert result is not None
    assert result.status == "CREATED"
    assert result.order.id == order.id

def test_order_step_unique_constraint(session):
    # Set up order as in previous test
    country = Country(code="IT", name="Italy", total_holidays=12, weekend_start=6, weekend_end=7)
    location = Location(name="Rome", city="Rome", state="RM", country_code="IT", latitude=41.9, longitude=12.5)
    carrier = Carrier(id=3, name="PosteItaliane", n_losses=0, n_orders=0)
    manufacturer = Manufacturer(name="Fiat", location_name="Rome")
    supplier = Supplier(manufacturer_supplier_id=100, name="Fiat Supplier")
    site = Site(supplier=supplier, location=location, n_rejections=0, n_orders=0)
    session.add_all([country, location, carrier, manufacturer, site])
    session.flush()

    order = Order(
        manufacturer_id=manufacturer.id,
        manufacturer_order_id=101,
        site_id=site.id,
        carrier_id=carrier.id,
        status="PROCESSING",
        n_steps=2,
        tracking_link=None,
        tracking_number="123",
        manufacturer_creation_timestamp=datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
        SLS=False
    )
    session.add(order)
    session.flush()

    step1 = OrderStep(order_id=order.id, step=1, status="CREATED", timestamp=datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc), location="Rome")
    step_duplicate = OrderStep(order_id=order.id, step=1, status="IN_PROGRESS", timestamp=datetime(2025, 6, 1, 11, 0, 0, tzinfo=timezone.utc), location="Rome")

    session.add(step1)
    session.commit()

    session.add(step_duplicate)
    with pytest.raises(IntegrityError):
        session.commit()

def test_create_order_step_enriched(session):
    country = Country(code="IT", name="Italy", total_holidays=12, weekend_start=6, weekend_end=7)
    location_site = Location(
        name="Rome",
        city="Rome",
        state="RM",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    carrier = Carrier(name="PosteItaliane", n_losses=0, n_orders=0)
    manufacturer = Manufacturer(name="Fiat", location_name="Rome")
    supplier = Supplier(manufacturer_supplier_id=100, name="Fiat Supplier")
    site = Site(supplier=supplier, location=location_site, n_rejections=0, n_orders=0)

    session.add_all([country, location_site, carrier, manufacturer, site])
    session.flush()

    # Create a minimal order
    order = Order(
        manufacturer_id=manufacturer.id,
        manufacturer_order_id=101,
        site_id=site.id,
        carrier=carrier,
        status="PROCESSING",
        n_steps=2,
        tracking_link=None,
        tracking_number="123",
        manufacturer_creation_timestamp=datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
        manufacturer_estimated_delivery_timestamp=None,
        manufacturer_confirmed_delivery_timestamp=None,
        carrier_creation_timestamp=None,
        carrier_estimated_delivery_timestamp=None,
        carrier_confirmed_delivery_timestamp=None,
        SLS=False
    )
    session.add(order)
    session.flush()

    location_source = Location(
        name="Milan",
        city="Milan",
        state="Lombardy",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    location_destination = Location(
        name="Naples",
        city="Naples",
        state="Campania",
        country_code="IT",
        latitude=40.8518,
        longitude=14.2681
    )
    session.add_all([location_source, location_destination])
    session.flush()

    # Act: insert OrderStepEnriched
    step = OrderStepEnriched(
        order_id=order.id,
        step_source=1,
        timestamp_source=datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
        location_name_source="Milan",
        step_destination=2,
        timestamp_destination=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        location_name_destination="Naples",
        hours=4.0,
        geodesic_km=100.0,
        distance_road_km=110.0,
        time_road_no_traffic_hours=3.5,
        time_road_traffic_hours=4.5
    )
    session.add(step)
    session.commit()

    # Assert: verify relationships and fields
    result = session.query(OrderStepEnriched).first()
    assert result is not None
    assert result.order.site.id == site.id
    assert result.order.manufacturer.name == "Fiat"
    assert result.step_source == 1
    assert result.location_source.name == location_source.name
    assert result.location_destination.name == location_destination.name
    assert result.timestamp_source == datetime(2025, 1, 1, 8, 0, 0) 
    assert result.step_destination == 2
    assert result.timestamp_destination == datetime(2025, 1, 1, 12, 0, 0)
    assert result.hours == 4.0
    assert result.geodesic_km == 100.0
    assert result.distance_road_km == 110.0
    assert result.time_road_no_traffic_hours == 3.5
    assert result.time_road_traffic_hours == 4.5

def test_order_step_enriched_unique_constraint(session):
    country = Country(code="IT", name="Italy", total_holidays=12, weekend_start=6, weekend_end=7)
    location_site = Location(
        name="Rome",
        city="Rome",
        state="RM",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    carrier = Carrier(name="PosteItaliane", n_losses=0, n_orders=0)
    manufacturer = Manufacturer(name="Fiat", location_name="Rome")
    supplier = Supplier(manufacturer_supplier_id=100, name="Fiat Supplier")
    site = Site(supplier=supplier, location=location_site, n_rejections=0, n_orders=0)

    session.add_all([country, location_site, carrier, manufacturer, site])
    session.flush()

    # Create a minimal order
    order = Order(
        manufacturer_id=manufacturer.id,
        manufacturer_order_id=101,
        site_id=site.id,
        carrier=carrier,
        status="PROCESSING",
        n_steps=2,
        tracking_link=None,
        tracking_number="123",
        manufacturer_creation_timestamp=datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
        manufacturer_estimated_delivery_timestamp=None,
        manufacturer_confirmed_delivery_timestamp=None,
        carrier_creation_timestamp=None,
        carrier_estimated_delivery_timestamp=None,
        carrier_confirmed_delivery_timestamp=None,
        SLS=False
    )
    session.add(order)
    session.flush()

    location_source = Location(
        name="Milan",
        city="Milan",
        state="Lombardy",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    location_destination = Location(
        name="Naples",
        city="Naples",
        state="Campania",
        country_code="IT",
        latitude=40.8518,
        longitude=14.2681
    )
    session.add_all([location_source, location_destination])
    session.flush()

    # Act: insert OrderStepEnriched
    step = OrderStepEnriched(
        order_id=order.id,
        step_source=1,
        timestamp_source=datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
        location_name_source="Milan",
        step_destination=2,
        timestamp_destination=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        location_name_destination="Naples",
        hours=4.0,
        geodesic_km=100.0,
        distance_road_km=110.0,
        time_road_no_traffic_hours=3.5,
        time_road_traffic_hours=4.5
    )
    session.add(step)
    session.commit()

    # Duplicate insert should fail due to unique constraint on (order_id, step_source)
    step2 = OrderStepEnriched(
        order_id=order.id,
        step_source=1,  # same step_source and order_id
        timestamp_source=datetime(2025, 1, 2, 8, 0, 0, tzinfo=timezone.utc),
        location_name_source="Naples",
        step_destination=3,
        timestamp_destination=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),  
        location_name_destination="Milan",
        hours=2.0,
        geodesic_km=20.0,
        distance_road_km=25.0,
        time_road_no_traffic_hours=1.8,
        time_road_traffic_hours=2.2
    )
    session.add(step2)
    with pytest.raises(Exception):
        session.commit()

def test_add_weather_data(session):
    country = Country(code="IT", name="Italy", total_holidays=12, weekend_start=6, weekend_end=7)
    location_site = Location(
        name="Rome",
        city="Rome",
        state="RM",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    carrier = Carrier(name="PosteItaliane", n_losses=0, n_orders=0)
    manufacturer = Manufacturer(name="Fiat", location_name="Rome")
    supplier = Supplier(manufacturer_supplier_id=100, name="Fiat Supplier")
    site = Site(supplier=supplier, location=location_site, n_rejections=0, n_orders=0)

    session.add_all([country, location_site, carrier, manufacturer, site])
    session.flush()

    # Create a minimal order
    order = Order(
        manufacturer_id=manufacturer.id,
        manufacturer_order_id=101,
        site_id=site.id,
        carrier=carrier,
        status="PROCESSING",
        n_steps=2,
        tracking_link=None,
        tracking_number="123",
        manufacturer_creation_timestamp=datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
        manufacturer_estimated_delivery_timestamp=None,
        manufacturer_confirmed_delivery_timestamp=None,
        carrier_creation_timestamp=None,
        carrier_estimated_delivery_timestamp=None,
        carrier_confirmed_delivery_timestamp=None,
        SLS=False
    )
    session.add(order)
    session.flush()

    location_source = Location(
        name="Milan",
        city="Milan",
        state="Lombardy",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    location_destination = Location(
        name="Naples",
        city="Naples",
        state="Campania",
        country_code="IT",
        latitude=40.8518,
        longitude=14.2681
    )
    session.add_all([location_source, location_destination])
    session.flush()

    # Act: insert OrderStepEnriched
    step = OrderStepEnriched(
        order_id=order.id,
        step_source=1,
        timestamp_source=datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
        location_name_source="Milan",
        step_destination=2,
        timestamp_destination=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        location_name_destination="Naples",
        hours=4.0,
        geodesic_km=100.0,
        distance_road_km=110.0,
        time_road_no_traffic_hours=3.5,
        time_road_traffic_hours=4.5
    )
    session.add(step)
    session.flush()

    # Add WeatherData referencing the above OrderStepEnriched
    weather_data = WeatherData(
        order_id=order.id,
        order_step_source=step.step_source,
        interpolation_step=1,
        latitude=45.0,
        longitude=9.0,
        step_distance_km=200.0,
        timestamp=datetime(2023, 1, 1, 0, 30, 0, tzinfo=timezone.utc),
        weather_codes="type_43,type_2",
        temperature_celsius=20.5
    )
    session.add(weather_data)
    session.commit()

    # Check that relationship is resolved
    result = session.query(WeatherData).first()
    assert result is not None
    assert result.order_step_enriched is not None
    assert result.order_step_enriched.id == step.id
    assert result.order_step_enriched.order_id == order.id
    assert result.order_step_enriched.step_source == step.step_source
    assert result.order_step_enriched.location_source.name == "Milan"
    assert result.order_step_enriched.location_destination.name == "Naples"
    assert result.order_step_enriched.timestamp_source == datetime(2025, 1, 1, 8, 0, 0)
    assert result.order_step_enriched.timestamp_destination == datetime(2025, 1, 1, 12, 0, 0)
    assert result.order_step_enriched.hours == 4.0
    assert result.weather_codes == weather_data.weather_codes
    assert result.temperature_celsius == weather_data.temperature_celsius 

def test_weather_data_unique_constraint(session):
    country = Country(code="IT", name="Italy", total_holidays=12, weekend_start=6, weekend_end=7)
    location_site = Location(
        name="Rome",
        city="Rome",
        state="RM",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    carrier = Carrier(name="PosteItaliane", n_losses=0, n_orders=0)
    manufacturer = Manufacturer(name="Fiat", location_name="Rome")
    supplier = Supplier(manufacturer_supplier_id=100, name="Fiat Supplier")
    site = Site(supplier=supplier, location=location_site, n_rejections=0, n_orders=0)

    session.add_all([country, location_site, carrier, manufacturer, site])
    session.flush()

    # Create a minimal order
    order = Order(
        manufacturer_id=manufacturer.id,
        manufacturer_order_id=101,
        site_id=site.id,
        carrier=carrier,
        status="PROCESSING",
        n_steps=2,
        tracking_link=None,
        tracking_number="123",
        manufacturer_creation_timestamp=datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
        manufacturer_estimated_delivery_timestamp=None,
        manufacturer_confirmed_delivery_timestamp=None,
        carrier_creation_timestamp=None,
        carrier_estimated_delivery_timestamp=None,
        carrier_confirmed_delivery_timestamp=None,
        SLS=False
    )
    session.add(order)
    session.flush()

    location_source = Location(
        name="Milan",
        city="Milan",
        state="Lombardy",
        country_code="IT",
        latitude=41.9028,
        longitude=12.4964
    )
    location_destination = Location(
        name="Naples",
        city="Naples",
        state="Campania",
        country_code="IT",
        latitude=40.8518,
        longitude=14.2681
    )
    session.add_all([location_source, location_destination])
    session.flush()

    # Act: insert OrderStepEnriched
    step = OrderStepEnriched(
        order_id=order.id,
        step_source=1,
        timestamp_source=datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
        location_name_source="Milan",
        step_destination=2,
        timestamp_destination=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        location_name_destination="Naples",
        hours=4.0,
        geodesic_km=100.0,
        distance_road_km=110.0,
        time_road_no_traffic_hours=3.5,
        time_road_traffic_hours=4.5
    )
    session.add(step)
    session.flush()

    # Add WeatherData referencing the above OrderStepEnriched
    weather_data = WeatherData(
        order_id=order.id,
        order_step_source=step.step_source,
        interpolation_step=1,
        latitude=45.0,
        longitude=9.0,
        step_distance_km=200.0,
        timestamp=datetime(2023, 1, 1, 0, 30, 0, tzinfo=timezone.utc),
        weather_codes="type_43,type_2",
        temperature_celsius=20.5
    )
    session.add(weather_data)
    session.commit()

    # Add second WeatherData with same unique keys
    wd2 =  WeatherData(
        order_id=order.id,
        order_step_source=step.step_source,
        interpolation_step=1,
        latitude=41.0,
        longitude=95.0,
        step_distance_km=100.0,
        timestamp=datetime(2023, 1, 1, 0, 30, 0, tzinfo=timezone.utc),
        weather_codes="type_11",
        temperature_celsius=12.5
    )
    session.add(wd2)
    with pytest.raises(Exception):
        session.commit()



def test_dispatch_time(session):
    # Setup: create country + location first
    country = Country(code="US", name="United States", total_holidays=10, weekend_start=6, weekend_end=7)
    session.add(country)
    session.flush()

    location = Location(
        name="NY",
        city="New York",
        state="NY",
        country_code="US",
        latitude=40.7128,
        longitude=-74.0060
    )
    session.add(location)
    session.flush()

    supplier = Supplier(manufacturer_supplier_id=100, name="Supplier A")
    site = Site(
        supplier=supplier,
        location=location,  # must pass Location instance, not string
        n_rejections=3,
        n_orders=12
    )
    session.add(site)
    session.commit()

    dt = DispatchTime(
        site=site,
        hours=1.2,
    )
    session.add(dt)
    session.commit()

    assert dt.site.location.name == "NY"
    assert dt.site.supplier.name == "Supplier A"
    assert dt.hours == 1.2

def test_dispatch_time_gamma(session):
    country = Country(code="US", name="United States", total_holidays=10, weekend_start=6, weekend_end=7)
    session.add(country)
    session.flush()

    location = Location(
        name="LA",
        city="Los Angeles",
        state="CA",
        country_code="US",
        latitude=34.0522,
        longitude=-118.2437
    )
    session.add(location)
    session.flush()

    supplier = Supplier(manufacturer_supplier_id=100, name="Supplier B")
    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=1,
        n_orders=5,
    )
    session.add(site)
    session.commit()

    dt_gamma = DispatchTimeGamma(
        site=site,
        shape=2.0,
        loc=0.0,
        scale=1.0,
        skewness=0.5,
        kurtosis=3.0,
        mean=2.0,
        std_dev=0.5,
        n=10
    )
    session.add(dt_gamma)
    session.commit()

    assert dt_gamma.site.location.name == "LA"
    assert dt_gamma.site.supplier.name == "Supplier B"
    assert dt_gamma.shape == 2.0

def test_dispatch_time_sample(session):
    country = Country(code="US", name="United States", total_holidays=10, weekend_start=6, weekend_end=7)
    session.add(country)
    session.flush()

    location = Location(
        name="SF",
        city="San Francisco",
        state="CA",
        country_code="US",
        latitude=37.7749,
        longitude=-122.4194
    )
    session.add(location)
    session.flush()

    supplier = Supplier(manufacturer_supplier_id=100, name="Supplier C")
    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=0,
        n_orders=8,
    )
    session.add(site)
    session.commit()

    dt_sample = DispatchTimeSample(
        site=site,
        median=1.5,
        mean=1.7,
        std_dev=0.3,
        n=15
    )
    session.add(dt_sample)
    session.commit()

    assert dt_sample.site.location.name == "SF"
    assert dt_sample.site.supplier.name == "Supplier C"
    assert dt_sample.median == 1.5



def test_create_shipment_time(session):
    country = Country(
        code="FR", name="France", total_holidays=11, weekend_start=6, weekend_end=7
    )
    location = Location(
        name="Paris",
        city="Paris",
        state="IDF",
        country_code="FR",
        latitude=48.8566,
        longitude=2.3522,
    )
    carrier = Carrier(name="DHL")
    supplier = Supplier(manufacturer_supplier_id=100, name="Supplier France")
    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=1,
        n_orders=20,
    )

    session.add_all([country, location, carrier, supplier, site])
    session.flush()  # assign IDs and FK references

    shipment_time = ShipmentTime(
        site_id=site.id,
        carrier=carrier,
        hours=12.5,
    )

    session.add(shipment_time)
    session.commit()

    result = session.query(ShipmentTime).filter_by(site_id=site.id).first()
    assert result is not None
    assert result.carrier.name == "DHL"
    assert result.hours == 12.5
    assert result.site.id == site.id

def test_create_shipment_time_gamma(session):
    # Create all dependencies
    country = Country(
        code="DE",
        name="Germany",
        total_holidays=12,
        weekend_start=6,
        weekend_end=7
    )
    location = Location(
        name="Berlin",
        city="Berlin",
        state="BE",
        country_code="DE",
        latitude=52.52,
        longitude=13.405
    )
    carrier = Carrier(name="UPS", n_losses=1, n_orders=3)
    supplier = Supplier(manufacturer_supplier_id=100, name="German Supplier")
    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=0,
        n_orders=50,
    )

    session.add_all([country, location, carrier, supplier, site])
    session.flush()

    # Create shipmentTimeGamma
    dt_gamma = ShipmentTimeGamma(
        site_id=site.id,
        carrier=carrier,
        shape=2.0,
        loc=0.0,
        scale=1.5,
        skewness=0.5,
        kurtosis=3.1,
        mean=3.0,
        std_dev=1.2,
        n=100
    )

    session.add(dt_gamma)
    session.commit()

    # Assertions
    result = session.query(ShipmentTimeGamma).filter_by(site_id=site.id).first()
    assert result is not None
    assert result.shape == 2.0
    assert result.loc == 0.0
    assert result.scale == 1.5
    assert result.skewness == 0.5
    assert result.kurtosis == 3.1
    assert result.mean == 3.0
    assert result.std_dev == 1.2
    assert result.n == 100
    assert result.site.id == site.id
    assert result.carrier.name == "UPS"

def test_create_shipment_time_sample(session):
    # Create dependencies
    country = Country(
        code="IT",
        name="Italy",
        total_holidays=15,
        weekend_start=6,
        weekend_end=7
    )
    location = Location(
        name="Milan",
        city="Milan",
        state="MI",
        country_code="IT",
        latitude=45.4642,
        longitude=9.1900
    )
    carrier = Carrier(name="DHL", n_losses=0, n_orders=1)
    supplier = Supplier(manufacturer_supplier_id=100, name="Italian Supplier")
    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=1,
        n_orders=100,
    )

    session.add_all([country, location, carrier, supplier, site])
    session.flush()

    # Create shipmentTimeSample
    sample = ShipmentTimeSample(
        site_id=site.id,
        carrier=carrier,
        median=24.0,
        mean=26.5,
        std_dev=3.2,
        n=80
    )

    session.add(sample)
    session.commit()

    # Assertions
    result = session.query(ShipmentTimeSample).filter_by(site_id=site.id).first()
    assert result is not None
    assert result.median == 24.0
    assert result.mean == 26.5
    assert result.std_dev == 3.2
    assert result.n == 80
    assert result.site.id == site.id
    assert result.carrier.name == "DHL"



def test_create_and_query_vertex(session):
    # Add a vertex
    vertex = Vertex(
        name="Plant A",
        type=VertexType.MANUFACTURER,
    )
    session.add(vertex)
    session.commit()

    fetched = session.query(Vertex).filter_by(name="Plant A").first()
    assert fetched is not None
    assert fetched.name == "Plant A"
    assert fetched.type == VertexType.MANUFACTURER

def test_vertex_uniqueness_constraint(session):
    vertex1 = Vertex(name="Depot 1", type=VertexType.SUPPLIER_SITE.value)
    vertex2 = Vertex(name="Depot 1", type=VertexType.SUPPLIER_SITE.value)  # Duplicate

    session.add(vertex1)
    session.commit()

    session.add(vertex2)
    with pytest.raises(IntegrityError):
        session.commit()

def test_create_route(session):
    source = Vertex(name="Source", type=VertexType.SUPPLIER_SITE.value)
    destination = Vertex(name="Destination", type=VertexType.MANUFACTURER.value)
    session.add_all([source, destination])
    session.commit()

    # Create a route
    route = Route(source_id=source.id, destination_id=destination.id)
    session.add(route)
    session.commit()

    # Fetch and assert
    retrieved = session.query(Route).first()
    assert retrieved.source_id == source.id
    assert retrieved.destination_id == destination.id
    assert retrieved.source.name == "Source"
    assert retrieved.destination.name == "Destination"

def test_route_unique_constraint(session):
    # Create vertices
    v1 = Vertex(name="A", type=VertexType.SUPPLIER_SITE.value)
    v2 = Vertex(name="B", type=VertexType.MANUFACTURER.value)
    session.add_all([v1, v2])
    session.commit()

    # First route
    session.add(Route(source_id=v1.id, destination_id=v2.id))
    session.commit()

    # Second identical route (should fail)
    session.add(Route(source_id=v1.id, destination_id=v2.id))
    with pytest.raises(IntegrityError):
        session.commit()
        session.rollback()

def test_create_route_order(session):
    # Setup test vertices
    v1 = Vertex(name="Vertex A", type="SUPPLIER_SITE")
    v2 = Vertex(name="Vertex B", type="MANUFACTURER")
    session.add_all([v1, v2])
    session.commit()

    country = Country(
        code="FR",
        name="France",
        total_holidays=11,
        weekend_start=6,
        weekend_end=7
    )
    session.add(country)

    location = Location(
        name="Paris, IDF, France",
        city="Paris",
        state="IDF",
        country_code="FR",
        latitude=48.8566,
        longitude=2.3522
    )
    session.add(location)

    carrier = Carrier(
        name="LaPoste",
        n_losses=1,
        n_orders=2
    )
    session.add(carrier)

    manufacturer = Manufacturer(
        name="Renault",
        location_name="Paris"
    )
    session.add(manufacturer)
    
    supplier = Supplier(manufacturer_supplier_id=100, name="Renault Supplier")
    session.add(supplier)
    session.commit()    

    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=0,
        n_orders=0,
    )
    session.add(site)
    session.commit()

    # Create the order
    order = Order(
        manufacturer_id=manufacturer.id,
        manufacturer_order_id=1001,
        site_id=site.id,
        carrier=carrier,
        status="CREATED",
        n_steps=3,
        tracking_link="http://track.me/123",
        tracking_number="123456789",
        manufacturer_creation_timestamp=datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
        manufacturer_estimated_delivery_timestamp=datetime(2025, 6, 10, 12, 0, 0, tzinfo=timezone.utc),
        manufacturer_confirmed_delivery_timestamp=None,
        carrier_creation_timestamp=datetime(2025, 6, 2, 8, 0, 0, tzinfo=timezone.utc),
        carrier_estimated_delivery_timestamp=datetime(2025, 6, 9, 18, 0, 0, tzinfo=timezone.utc),
        carrier_confirmed_delivery_timestamp=None,
        SLS=True
    )
    session.add(order)
    session.commit()

    # Create RouteOrder
    route_order = RouteOrder(
        source_id=v1.id,
        destination_id=v2.id,
        order_id=order.id,
    )
    session.add(route_order)
    session.commit()

    # Query back
    ro = session.query(RouteOrder).filter_by(id=route_order.id).one()

    assert ro.source_id == v1.id
    assert ro.destination_id == v2.id
    assert ro.order_id == order.id

    # Check relationship objects
    assert ro.source.name == "Vertex A"
    assert ro.destination.name == "Vertex B"
    assert ro.order.id == order.id

    # Test uniqueness constraint: adding duplicate RouteOrder should raise IntegrityError
    duplicate = RouteOrder(
        source_id=v1.id,
        destination_id=v2.id,
        order_id=order.id,
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()



def test_create_oti(session):
    source = Vertex(name="Supplier A", type=VertexType.SUPPLIER_SITE.value)
    destination = Vertex(name="Manufacturer B", type=VertexType.MANUFACTURER.value)
    session.add_all([source, destination])
    session.commit()

    oti = OTI(
        source_id=source.id,
        destination_id=destination.id,
        hours=48.5
    )
    session.add(oti)
    session.commit()

    # Fetch and verify
    result = session.query(OTI).first()
    assert result is not None
    assert result.source_id == source.id
    assert result.destination_id == destination.id
    assert result.hours == 48.5
    assert result.source.name == "Supplier A"
    assert result.destination.name == "Manufacturer B"

def test_oti_missing_fields(session):
    source = Vertex(name="Node A", type=VertexType.INTERMEDIATE.value)
    destination = Vertex(name="Node B", type=VertexType.MANUFACTURER.value)
    session.add_all([source, destination])
    session.commit()

    # Missing hours
    oti = OTI(
        source_id=source.id,
        destination_id=destination.id,
    )
    session.add(oti)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

def test_create_valid_ori(session):
    vertex = Vertex(name="Warehouse A", type=VertexType.INTERMEDIATE.value)
    session.add(vertex)
    session.commit()

    ori = ORI(vertex_id=vertex.id, hours=42.5)
    session.add(ori)
    session.commit()

    result = session.query(ORI).first()
    assert result is not None
    assert result.vertex_id == vertex.id
    assert result.hours == 42.5

def test_missing_created_at_or_hours_raises_error(session):
    vertex = Vertex(name="Hub B", type=VertexType.INTERMEDIATE.value)
    session.add(vertex)
    session.commit()

    ori_missing_hours = ORI(vertex_id=vertex.id)
    session.add(ori_missing_hours)
    with pytest.raises(IntegrityError):
        session.commit()

def test_create_params(session):
    param = Param(
        name="Test Param",
        general_category="Test General Category",
        category="Test category",
        value=0.7,
        description="This is a test parameter",
    )
    session.add(param)
    session.commit()

    # Fetch and verify
    result = session.query(Param).first()
    assert result is not None
    assert result.name == "Test Param"
    assert result.value == 0.7
    assert result.description == "This is a test parameter"

    with pytest.raises(IntegrityError):
        # Attempt to create a duplicate Param with the same name
        duplicate_param = Param(
            name="Test Param",
            value=0.2,
            description="This should fail due to unique constraint",
        )
        session.add(duplicate_param)
        session.commit()
 

def test_create_alpha_opt(session):
    country = Country(
        code="FR", name="France", total_holidays=11, weekend_start=6, weekend_end=7
    )
    location = Location(
        name="Paris",
        city="Paris",
        state="IDF",
        country_code="FR",
        latitude=48.8566,
        longitude=2.3522,
    )
    carrier = Carrier(name="DHL")
    supplier = Supplier(manufacturer_supplier_id=100, name="Supplier France")
    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=1,
        n_orders=20,
    )

    session.add_all([country, location, carrier, supplier, site])
    session.flush()  # assign IDs and FK references

    alpha_opt = AlphaOpt(
        site_id=site.id,
        carrier=carrier,
        tt_weight=0.6,
    )

    session.add(alpha_opt)
    session.commit()

    result = session.query(AlphaOpt).first()
    assert result is not None
    assert result.site_id == site.id
    assert result.carrier.name == "DHL"
    assert result.tt_weight == 0.6

    with pytest.raises(Exception):
        # Attempt to add a duplicate AlphaOpt for the same site and carrier
        duplicate_alpha_opt = AlphaOpt(
            site_id=site.id,
            carrier_name=carrier.name,
            tt_weight=0.8,  # Different weight but same site and carrier
        )
        session.add(duplicate_alpha_opt)
        session.commit()

def test_create_alpha(session):
    alpha_const = Alpha(
        type=AlphaType.CONST,
        input=0.3,
        value=0.8,
    )
    session.add(alpha_const)
    session.commit()

    # Fetch and verify
    result = session.query(Alpha).first()
    assert result is not None
    assert result.input == 0.3
    assert result.value == 0.8

    alpha_exp = Alpha(
        type=AlphaType.EXP,
        tt_weight=0.1,
        tau=0.2,
        input=0.5,
        value=0.9,
    )
    session.add(alpha_exp)
    session.commit()

    # Fetch and verify
    result_exp = session.query(Alpha).filter_by(type=AlphaType.EXP).first()
    assert result_exp is not None
    assert result_exp.tt_weight == 0.1
    assert result_exp.tau == 0.2
    assert result_exp.input == 0.5

    alpha_markov = Alpha(
        type=AlphaType.MARKOV,
        tau=0.4,
        gamma=0.6,
        input=0.4,
        value=0.95,
    )
    session.add(alpha_markov)
    session.commit()
    
    # Fetch and verify
    result_markov = session.query(Alpha).filter_by(type=AlphaType.MARKOV).first()
    assert result_markov is not None
    assert result_markov.tau == 0.4
    assert result_markov.gamma == 0.6
    assert result_markov.input == 0.4

def test_create_time_deviation(session):
    time_deviation = TimeDeviation(
        dt_hours_lower=1.0,
        dt_hours_upper=2.0,
        st_hours_lower=0.5,
        st_hours_upper=1.5,
        dt_confidence=0.9,
        st_confidence=0.8,
    )
    session.add(time_deviation)
    session.commit()

    # Fetch and verify
    result = session.query(TimeDeviation).first()
    assert result is not None
    assert result.dt_hours_lower == 1.0
    assert result.dt_hours_upper == 2.0
    assert result.st_hours_lower == 0.5
    assert result.st_hours_upper == 1.5
    assert result.dt_confidence == 0.9
    assert result.st_confidence == 0.8

def test_create_estimated_time(session):
    # Create a Vertex record
    vertex = Vertex(name="Test Vertex", type=VertexType.SUPPLIER_SITE.value)
    session.add(vertex)
    session.commit()

    # Create minimal dependencies for Order
    country = Country(
        code="US",
        name="United States",
        total_holidays=10,
        weekend_start=6,
        weekend_end=7
    )
    session.add(country)
    holiday = Holiday(
        country_code="US",
        date=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        name="New Year's Day",
        description="Celebration of the new year",
        category=HolidayCategory.CLOSURE,
        url="https://en.wikipedia.org/wiki/New_Year%27s_Day",
        type="Public Holiday",
        week_day=3,  # Wednesday
        month=1,
        year_day=1
    )
    session.add(holiday)
    location = Location(
        name="Dummy Location",
        city="DummyCity",
        state="DC",
        country_code="US",
        latitude=0.0,
        longitude=0.0
    )
    session.add(location)
    supplier = Supplier(manufacturer_supplier_id=100, name="Dummy Supplier")
    session.add(supplier)
    session.commit()
    site = Site(
        supplier=supplier,
        location=location,
        n_rejections=0,
        n_orders=0,
    )
    session.add(site)
    session.commit()
    carrier = Carrier(name="FedEx", n_losses=0, n_orders=0)
    session.add(carrier)
    session.commit()
    manufacturer = Manufacturer(name="Dummy Manufacturer", location_name="Dummy Location")
    session.add(manufacturer)
    session.commit()

    # Create a minimal Order record
    order_obj = Order(
        manufacturer_id=manufacturer.id,
        manufacturer_order_id=1234,
        site_id=site.id,
        carrier=carrier,
        status="CREATED",
        n_steps=1,
        tracking_link="http://dummy",
        tracking_number="123456789",
        manufacturer_creation_timestamp=datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc),
        manufacturer_estimated_delivery_timestamp=datetime(2025, 6, 2, 0, 0, 0, tzinfo=timezone.utc),
        manufacturer_confirmed_delivery_timestamp=None,
        carrier_creation_timestamp=datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc),
        carrier_estimated_delivery_timestamp=datetime(2025, 6, 2, 0, 0, 0, tzinfo=timezone.utc),
        carrier_confirmed_delivery_timestamp=None,
        SLS=False
    )
    session.add(order_obj)
    session.commit()

    alpha = Alpha(
        tt_weight=0.1,
        type=AlphaType.CONST,
        input=0.3,
        value=0.8
    )
    session.add(alpha)
    session.commit()

    time_deviation = TimeDeviation(
        dt_hours_lower=1.0,
        dt_hours_upper=2.0,
        st_hours_lower=0.5,
        st_hours_upper=1.5,
        dt_confidence=0.9,
        st_confidence=0.8,
    )
    session.add(time_deviation)
    session.commit()

    estimation_params: EstimationParams = EstimationParams(
        dt_confidence=0.8,
        consider_closure_holidays=True,
        consider_working_holidays=False,
        consider_weekends_holidays=True,
        rte_mape=0.9,
        use_rte_model=True,
        use_traffic_service=True,
        tmi_max_timediff_hours=1.0,
        use_weather_service=True,
        wmi_max_timediff_hours=1.0,
        wmi_step_distance_km=100.0,
        wmi_max_points=10,
        pt_path_min_prob=0.1,
        pt_max_paths=5,
        pt_ext_data_min_prob=0.2,
        pt_confidence=0.5,
        tt_confidence=0.3,
        tfst_tolerance=0.01,
    )
    session.add(estimation_params)
    session.commit()

    # Create an EstimatedDeliveryTime record with fields matching the model
    estimated_delivery = EstimatedTime(
        vertex_id=vertex.id,
        order_id=order_obj.id,
        shipment_time=datetime(2025, 6, 3, 10, 0, 0, tzinfo=timezone.utc),
        event_time=datetime(2025, 6, 3, 10, 2, 0, tzinfo=timezone.utc),
        estimation_time=datetime(2025, 6, 3, 10, 4, 0, tzinfo=timezone.utc),
        status="SHIPMENT",
        DT_weekend_days=1,
        DT=45.0,
        DT_lower=40.0,
        DT_upper=50.0,
        TT_lower=18.0,
        TT_upper=22.0,
        PT_n_paths=3,
        PT_avg_tmi=0.1,
        PT_avg_wmi=0.2,
        PT_lower=15.0,
        PT_upper=25.0,
        TFST_lower=10.0,
        TFST_upper=12.0,
        EST=5.0,
        EODT=3.0,
        CFDI_lower=2.0,
        CFDI_upper=4.0,
        EDD=datetime(2025, 6, 5, 10, 0, 0, tzinfo=timezone.utc),
        time_deviation=time_deviation,
        alpha_id=alpha.id,
        estimation_params_id=estimation_params.id
    )
    session.add(estimated_delivery)
    session.commit()

    estimated_time_holiday = EstimatedTimeHoliday(
        estimated_time_id=estimated_delivery.id,
        holiday_id=holiday.id,
    )
    session.add(estimated_time_holiday)
    session.commit()

    # Fetch the record and assert its fields and relationships
    result: EstimatedTime = session.query(EstimatedTime).filter_by(id=estimated_delivery.id).first()
    assert result is not None
    assert result.vertex_id == vertex.id
    assert result.order_id == order_obj.id
    assert result.shipment_time == datetime(2025, 6, 3, 10, 0, 0)
    assert result.event_time == datetime(2025, 6, 3, 10, 2, 0)
    assert result.estimation_time == datetime(2025, 6, 3, 10, 4, 0)
    assert result.DT_weekend_days == 1
    assert result.DT_lower == 40.0
    assert result.DT_upper == 50.0
    assert result.PT_n_paths == 3
    assert result.PT_avg_tmi == 0.1
    assert result.PT_avg_wmi == 0.2
    assert result.TT_lower == 18.0
    assert result.TT_upper == 22.0
    assert result.PT_lower == 15.0
    assert result.PT_upper == 25.0
    assert result.TFST_lower == 10.0
    assert result.TFST_upper == 12.0
    assert result.EST == 5.0
    assert result.EODT == 3.0
    assert result.CFDI_lower == 2.0
    assert result.CFDI_upper == 4.0
    assert result.EDD == datetime(2025, 6, 5, 10, 0, 0)
    assert result.time_deviation.dt_hours_lower == 1.0
    assert result.time_deviation.dt_hours_upper == 2.0
    assert result.time_deviation.st_hours_lower == 0.5
    assert result.time_deviation.st_hours_upper == 1.5
    assert result.time_deviation.dt_confidence == 0.9
    assert result.time_deviation.st_confidence == 0.8
    assert result.alpha.tt_weight == 0.1
    assert result.alpha.input == 0.3
    assert result.alpha.value == 0.8
    assert result.estimation_params.consider_closure_holidays is True
    assert result.estimation_params.consider_working_holidays is False
    assert result.estimation_params.consider_weekends_holidays is True
    assert result.estimation_params.rte_mape == 0.9
    assert result.estimation_params.use_traffic_service is True
    assert result.estimation_params.tmi_max_timediff_hours == 1.0
    assert result.estimation_params.use_weather_service is True
    assert result.estimation_params.wmi_max_timediff_hours == 1.0
    assert result.holidays is not None
    assert len(result.holidays) == 1

    holiday_result = session.query(EstimatedTimeHoliday).filter_by(estimated_time_id=estimated_delivery.id).first()
    assert holiday_result is not None
    assert holiday_result.holiday_id == holiday.id


def test_create_wmi(session):
    # Add source and destination vertices
    source = Vertex(name="SourceNode", type=VertexType.SUPPLIER_SITE.value)
    destination = Vertex(name="DestinationNode", type=VertexType.INTERMEDIATE.value)
    session.add_all([source, destination])
    session.commit()

    wmi = WMI(
        source_id=source.id,
        destination_id=destination.id,
        created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        timestamp=datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
        n_interpolation_points=5,
        step_distance_km=2.5,
        value=42.0
    )

    session.add(wmi)
    session.commit()

    # Reload to ensure relationship binding
    wmi_from_db = session.query(WMI).first()

    assert wmi_from_db.source.name == "SourceNode"
    assert wmi_from_db.destination.name == "DestinationNode"
    assert wmi_from_db.n_interpolation_points == 5
    assert wmi_from_db.step_distance_km == 2.5
    assert wmi_from_db.value == 42.0

def test_create_tmi(session):
    # Arrange: create source and destination vertices
    source = Vertex(name="Source", type=VertexType.SUPPLIER_SITE.value)
    destination = Vertex(name="Destination", type=VertexType.MANUFACTURER.value)
    session.add_all([source, destination])
    session.commit()

    # Act: insert a TMI instance
    tmi = TMI(
        source_id=source.id,
        destination_id=destination.id,
        created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        timestamp=datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
        transportation_mode=TransportationMode.ROAD,
        value=123.45
    )
    session.add(tmi)
    session.commit()

    # Assert: fetch and verify
    result = session.query(TMI).first()
    assert result is not None
    assert result.source_id == source.id
    assert result.destination_id == destination.id
    assert result.transportation_mode == TransportationMode.ROAD
    assert result.value == 123.45
    assert result.source.name == "Source"
    assert result.destination.name == "Destination"