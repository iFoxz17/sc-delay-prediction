import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import contextlib
import boto3

from model.base import Base
from model.country import Country
from model.location import Location
from model.site import Site
from model.supplier import Supplier
from model.carrier import Carrier
from model.manufacturer import Manufacturer
from model.order import Order, OrderStatus

from service.read_only_db_connector import ReadOnlyDBConnector
from service.db_connector import DBConnector

from model_dto.order_patch_dto import OrderPatchDTO
from model_dto.q_params import By

from model_service.exception.order_not_found_exception import OrderNotFoundException
from model_service.order_service import get_order_by_id, get_orders, patch_order_by_id 

#--------------------------------------------------------------
# Setup
#--------------------------------------------------------------

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
    dhl = Carrier(name="dhl", carrier_17track_id="1000")
    fedex = Carrier(name="fedex", carrier_17track_id="2000")
    session.add_all([dhl, fedex])
    session.commit()

    # --- Sites ---
    site1 = Site(id=1, supplier_id=10, location_name="Location A", n_rejections=0, n_orders=2)
    site2 = Site(id=2, supplier_id=10, location_name="Location B", n_rejections=0, n_orders=1)
    session.add_all([site1, site2])
    session.commit()

    # --- Orders ---
    orders = [
        Order(id=1, manufacturer_id=manufacturer.id, manufacturer_order_id=101, site_id=1, carrier=dhl, status=OrderStatus.PENDING.value, n_steps=3, tracking_link=None, tracking_number="123", manufacturer_creation_timestamp=datetime(2025, 6, 1, 9, 0, 0), SLS=False),
        Order(id=2, manufacturer_id=manufacturer.id, manufacturer_order_id=102, site_id=1, carrier=fedex, status=OrderStatus.IN_TRANSIT.value, n_steps=4, tracking_link=None, tracking_number="456", manufacturer_creation_timestamp=datetime(2025, 6, 2, 10, 0, 0), SLS=False),
        Order(id=3, manufacturer_id=manufacturer.id, manufacturer_order_id=103, site_id=2, carrier=dhl, status=OrderStatus.DELIVERED.value, n_steps=5, tracking_link=None, tracking_number="789", manufacturer_creation_timestamp=datetime(2025, 6, 3, 11, 0, 0), SLS=False),
    ]
    session.add_all(orders)
    session.commit()

    return session

@pytest.fixture(scope="function")
def patch_ro_connector(in_memory_db, seed_data, mocker):
    class TestROConnector(ReadOnlyDBConnector):
        def __init__(self, _: str):
            # Use a factory that returns the same in-memory session
            self._session = in_memory_db

        @contextlib.contextmanager
        def session_scope(self):
            try:
                yield self._session
            finally:
                pass  # The session will be closed by pytest fixture

    mocker.patch("service.db_utils.ReadOnlyDBConnector", new=TestROConnector)

@pytest.fixture(scope="function")
def patch_connector(in_memory_db, seed_data, mocker):
    class TestConnector(DBConnector):
        def __init__(self, _: str):
            # Use a factory that returns the same in-memory session
            self._session = in_memory_db

        @contextlib.contextmanager
        def session_scope(self):
            try:
                yield self._session
            finally:
                pass  # The session will be closed by pytest fixture

    mocker.patch("service.db_utils.DBConnector", new=TestConnector)
    return TestConnector("test")


@pytest.fixture(scope="function")
def mock_db_env(monkeypatch):
    database_secret_arn = "sqlite:///:memory:"
    region = "eu-west-1"

    monkeypatch.setenv("DATABASE_SECRET_ARN", database_secret_arn)
    monkeypatch.setenv("AWS_REGION", region)

    creds = '''
    {
        "username": "mockuser",
        "password": "mockpass",
        "host":     "mockhost",
        "port":     5432,
        "dbname":   "mockdb"
    }
    '''

    class MockClient:
        def get_secret_value(self, SecretId):
            return {"SecretString": creds}

    monkeypatch.setattr(
        boto3,
        "client",
        lambda service_name, region_name=None: MockClient()
    )
    
#--------------------------------------------------------------
# Tests
#--------------------------------------------------------------

def test_get_all_orders(mock_db_env, patch_ro_connector):
    orders_json = get_orders()

    assert len(orders_json) == 3
    assert orders_json[0]["order_id"] == 1
    assert orders_json[0]["manufacturer_order_id"] == 101
    assert orders_json[0]["site"]["id"] == 1
    assert orders_json[0]["site"]["location"] == "Location A"
    assert orders_json[0]["supplier"]["id"] == 10
    assert orders_json[0]["supplier"]["manufacturer_id"] == 100
    assert orders_json[0]["supplier"]["name"] == "Supplier A"
    assert orders_json[0]["carrier"]["id"] == 1
    assert orders_json[0]["carrier"]["name"] == "dhl"
    assert orders_json[0]["SLS"] is False
    assert orders_json[0]["status"] == "PENDING"

def test_get_filtered_orders(mock_db_env, patch_ro_connector):
    q_params = {"status": "IN_TRANSIT,DELIVERED"}
    orders_json = get_orders(q_params=q_params)

    assert len(orders_json) == 2

    assert orders_json[0]["order_id"] == 2
    assert orders_json[0]["manufacturer_order_id"] == 102
    assert orders_json[0]["site"]["id"] == 1
    assert orders_json[0]["site"]["location"] == "Location A"
    assert orders_json[0]["supplier"]["id"] == 10
    assert orders_json[0]["supplier"]["manufacturer_id"] == 100
    assert orders_json[0]["supplier"]["name"] == "Supplier A"
    assert orders_json[0]["carrier"]["id"] == 2
    assert orders_json[0]["carrier"]["name"] == "fedex"
    assert orders_json[0]["SLS"] is False
    assert orders_json[0]["status"] == "IN_TRANSIT"

    assert orders_json[1]["order_id"] == 3
    assert orders_json[1]["manufacturer_order_id"] == 103
    assert orders_json[1]["site"]["id"] == 2
    assert orders_json[1]["site"]["location"] == "Location B"
    assert orders_json[1]["supplier"]["id"] == 10
    assert orders_json[1]["supplier"]["manufacturer_id"] == 100
    assert orders_json[1]["supplier"]["name"] == "Supplier A"
    assert orders_json[1]["carrier"]["id"] == 1
    assert orders_json[1]["carrier"]["name"] == "dhl"
    assert orders_json[1]["SLS"] is False
    assert orders_json[1]["status"] == "DELIVERED"

def test_get_order_by_id(mock_db_env, patch_ro_connector):
    order_json = get_order_by_id(1)
    assert order_json["order_id"] == 1

    assert order_json["manufacturer_order_id"] == 101
    assert order_json["site"]["id"] == 1
    assert order_json["site"]["location"] == "Location A"
    assert order_json["supplier"]["id"] == 10
    assert order_json["supplier"]["manufacturer_id"] == 100
    assert order_json["supplier"]["name"] == "Supplier A"
    assert order_json["carrier"]["id"] == 1
    assert order_json["carrier"]["name"] == "dhl"
    assert order_json["SLS"] is False
    assert order_json["status"] == "PENDING"


def test_patch_order_srs_true(mock_db_env, patch_connector):
    patch_data = OrderPatchDTO(srs=True)
    result = patch_order_by_id(1, By.ID, patch_data)

    assert result["order_id"] == 1
    assert result["SRS"] is True
    
    with patch_connector.session_scope() as session:
        session = patch_connector._session
        site = session.query(Site).filter(Site.id == 1).one()
        assert site.n_rejections == 1

    result1 = patch_order_by_id(101, By.MANUFACTURER_ID, OrderPatchDTO(srs=True))
    assert result1["SRS"] is True  # Should remain True

    with patch_connector.session_scope() as session:
        session = patch_connector._session
        site = session.query(Site).filter(Site.id == 1).one()
        assert site.n_rejections == 1


def test_patch_order_srs_false(mock_db_env, patch_connector):
    # First set it to True
    patch_order_by_id(1, By.ID, OrderPatchDTO(srs=True))

    # Then patch to False
    patch_data = OrderPatchDTO(srs=False)
    result = patch_order_by_id(1, By.ID, patch_data)

    assert result["SRS"] is False

    with patch_connector.session_scope() as session:
        session = patch_connector._session
        site = session.query(Site).filter(Site.id == 1).one()
        assert site.n_rejections == 0  # Should decrement back to 0

    
    result1 = patch_order_by_id(101, By.MANUFACTURER_ID, OrderPatchDTO(srs=False))
    assert result1["SRS"] is False  # Should remain False
    
    with patch_connector.session_scope() as session:
        session = patch_connector._session
        site = session.query(Site).filter(Site.id == 1).one()
        assert site.n_rejections == 0

def test_patch_order_srs_no_change(mock_db_env, patch_connector):
    # Ensure SRS is False first
    patch_order_by_id(1, By.ID, OrderPatchDTO(srs=False))

    # Now apply patch with same value again
    result = patch_order_by_id(1, By.ID, OrderPatchDTO(srs=False))

    assert result["SRS"] is False

    with patch_connector.session_scope() as session:
        session = patch_connector._session
        site = session.query(Site).filter(Site.id == 1).one()
        assert site.n_rejections == 0  # Should not change


def test_patch_order_not_found(mock_db_env, patch_connector):
    with pytest.raises(OrderNotFoundException):
        patch_order_by_id(9999, By.ID, OrderPatchDTO(srs=True))
