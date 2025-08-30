import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import contextlib
import boto3

from model.base import Base
from model.country import Country
from model.location import Location
from model.site import Site
from model.supplier import Supplier

from hist_service.dri.dri_service import calculate_dri
from service.read_only_db_connector import ReadOnlyDBConnector
from hist_service.dispatch_time.dispatch_time_service import ReadOnlyDBConnector

#--------------------------------------------------------------
# Setup
#--------------------------------------------------------------

# Create a new in-memory SQLite DB engine - no need to clean up after tests because of scope="function"
@pytest.fixture(scope="function")
def in_memory_db():
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    yield SessionLocal
    engine.dispose()

# Setup the database with initial data for testing
@pytest.fixture(scope="function")
def seed_data(in_memory_db):
    # Insert some test data
    session = in_memory_db()

    # Countries
    country = Country(code="IT", name="Italy", total_holidays=10, weekend_start=6, weekend_end=7)
    session.add(country)
    session.commit()

    # Locations
    locations = [
        Location(name="Location A", city="A", state="AA", country_code="IT", latitude=0, longitude=0),
        Location(name="Location B", city="B", state="BB", country_code="IT", latitude=1, longitude=1),
        Location(name="Location C", city="C", state="CC", country_code="IT", latitude=2, longitude=2),
        Location(name="Location D", city="D", state="DD", country_code="IT", latitude=3, longitude=3),
    ]
    session.add_all(locations)
    session.commit()

    # Suppliers
    supplier1 = Supplier(id=10, manufacturer_supplier_id=1, name="Supplier A")
    supplier2 = Supplier(id=20, manufacturer_supplier_id=2, name="Supplier B")
    supplier3 = Supplier(id=30, manufacturer_supplier_id=3, name="Supplier C")
    session.add_all([supplier1, supplier2, supplier3])

    # Sites
    site1 = Site(id=1, supplier_id=10, location_name="Location A", n_rejections=5, n_orders=100)
    site2 = Site(id=2, supplier_id=10, location=locations[1], n_rejections=3, n_orders=10)
    site3 = Site(id=3, supplier_id=20, location_name="Location C", n_rejections=0, n_orders=5)
    site4 = Site(id=4, supplier_id=30, location=locations[3], n_rejections=1, n_orders=5)
    site5 = Site(id=5, supplier_id=20, location_name="Location D", n_rejections=0, n_orders=0)
    session.add_all([site1, site2, site3, site4, site5])
    session.commit()
    session.close()

# Patch the ReadOnlyDBConnector to use the in-memory database
@pytest.fixture(scope="function")
def patch_connector(in_memory_db, seed_data, mocker):
    class TestConnector(ReadOnlyDBConnector):
        def __init__(self, _: str):
            self._SessionLocal = in_memory_db

        @contextlib.contextmanager
        def session_scope(self):
            session = self._SessionLocal()
            try:
                yield session
            finally:
                session.close()

    mocker.patch("service.db_utils.ReadOnlyDBConnector", new=TestConnector)

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

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dri_no_params(mock_db_env):
    q_params = {}

    body = calculate_dri(q_params)
    assert isinstance(body, list)

    # All sites with at least one order expected
    site_ids = {entry["site"]['id'] for entry in body}
    assert site_ids == {1, 2, 3, 4}

    # Suppliers corresponding to those sites
    supplier_ids = {entry["supplier"]['id'] for entry in body}
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "indicators" in entry
        assert "DRI" in entry["indicators"]

# ------------------------------
# Single Site and Supplier Tests
# ------------------------------

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dri_only_supplier(mock_db_env):
    q_params = {
        "supplier": "10"
    }

    body = calculate_dri(q_params)
    assert isinstance(body, list)

    # Supplier 10 has sites 1 and 2, so these sites expected
    site_ids = {entry["site"]['id'] for entry in body}
    assert site_ids == {1, 2}

    supplier_ids = {entry["supplier"]['id'] for entry in body}
    assert supplier_ids == {10}

    for entry in body:
        assert "indicators" in entry
        assert "DRI" in entry["indicators"]

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_only_site(mock_db_env):
    q_params = {
        "site": "3"
    }

    body = calculate_dri(q_params)
    assert isinstance(body, list)

    # Only site 3 expected
    site_ids = {entry["site"]['id'] for entry in body}
    assert site_ids == {3}

    # Site 3 belongs to supplier 20
    supplier_ids = {entry["supplier"]['id'] for entry in body}
    assert supplier_ids == {20}

    for entry in body:
        assert "indicators" in entry
        assert "DRI" in entry["indicators"]
        
@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_supplier_and_site(mock_db_env):
    q_params = {
        "supplier": "10",
        "site": "3"
    }

    body = calculate_dri(q_params)
    assert isinstance(body, list)
    
    site_ids = {entry["site"]['id'] for entry in body}
    assert site_ids == {1, 2, 3}
    
    supplier_ids = {entry["supplier"]['id'] for entry in body}
    assert supplier_ids == {10, 20}

    for entry in body:
        assert "indicators" in entry
        assert "DRI" in entry["indicators"]


# ------------------------------
# Multiple Sites and Suppliers Tests
# ------------------------------

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_multiple_sites(mock_db_env):
    q_params = {
        "site": "2,3,4"
    }

    body = calculate_dri(q_params)
    assert isinstance(body, list)

    # Sites 2, 3, 4 expected
    site_ids = {entry["site"]['id'] for entry in body}
    assert site_ids == {2, 3, 4}

    # Suppliers corresponding to those sites
    supplier_ids = {entry["supplier"]['id'] for entry in body}
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "indicators" in entry
        assert "DRI" in entry["indicators"]
