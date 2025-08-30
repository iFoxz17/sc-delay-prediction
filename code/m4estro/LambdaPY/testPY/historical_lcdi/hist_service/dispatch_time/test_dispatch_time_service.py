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
from model.dispatch_time_gamma import DispatchTimeGamma
from model.dispatch_time_sample import DispatchTimeSample
from model.dispatch_time import DispatchTime
from model.param import Param, ParamName, ParamCategory, ParamGeneralCategory

from hist_service.dispatch_time.dispatch_time_service import calculate_dispatch_time 
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
    site2 = Site(id=2, supplier_id=10, location=locations[1], n_rejections=3, n_orders=80)
    site3 = Site(id=3, supplier_id=20, location_name="Location C", n_rejections=2, n_orders=18)
    site4 = Site(id=4, supplier_id=30, location=locations[3], n_rejections=1, n_orders=12)
    site5 = Site(id=5, supplier_id=20, location_name="Location D", n_rejections=0, n_orders=0)
    session.add_all([site1, site2, site3, site4, site5])

    # DispatchTime records
    dt1 = DispatchTime(site_id=1, hours=2.5)
    dt2 = DispatchTime(site_id=2, hours=3.0)
    dt3 = DispatchTime(site_id=3, hours=1.5)
    dt4 = DispatchTime(site_id=4, hours=4.0)
    dt5 = DispatchTime(site_id=1, hours=2.0)
    dt6 = DispatchTime(site_id=2, hours=3.5)
    dt7 = DispatchTime(site_id=3, hours=1.0)
    dt8 = DispatchTime(site_id=4, hours=4.5)
    dt9 = DispatchTime(site_id=1, hours=2.2)
    dt10 = DispatchTime(site_id=2, hours=3.2)
    session.add_all([dt1, dt2, dt3, dt4, dt5, dt6, dt7, dt8, dt9, dt10])

    # DispatchTimeGamma records
    gamma1 = DispatchTimeGamma(
        id=1, site_id=1, shape=1.0, loc=0.5, scale=2.0,
        skewness=0.1, kurtosis=3.0, mean=5.0, std_dev=1.5, n=100
    )
    gamma2 = DispatchTimeGamma(
        id=2, site_id=2, shape=2.0, loc=1.5, scale=3.0,
        skewness=0.2, kurtosis=4.0, mean=6.0, std_dev=1.8, n=80
    )

    # DispatchTimeSample records
    sample1 = DispatchTimeSample(
        id=1, site_id=3, median=3.4, mean=4.0, std_dev=1.2, n=18,
    )
    sample2 = DispatchTimeSample(
        id=2, site_id=4, median=3.1, mean=6.0, std_dev=1.98, n=12,
    )

    session.add_all([gamma1, gamma2, sample1, sample2])
    session.commit()

    cl = Param(
        name=ParamName.DISPATCH_HIST_CONFIDENCE.value, 
        general_category=ParamGeneralCategory.HISTORICAL.value,
        category=ParamCategory.SHIPMENT_TIME.value,
        value=0.95, description="Confidence level for dispatch time calculations")
    
    session.add(cl)
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

# ------------------------------
# Single Site and Supplier Tests
# ------------------------------


@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_only_supplier(mock_db_env):
    q_params = {
        "supplier": "10"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Supplier 10 has sites 1 and 2, so these sites expected
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]['id'] for entry in body}
    assert site_ids == {1, 2}

    assert 'id' in body[0]['supplier']
    assert 'name' in body[0]['supplier']
    supplier_ids = {entry["supplier"]['id'] for entry in body}
    assert supplier_ids == {10}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_only_site(mock_db_env):
    q_params = {
            "site": "3"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Only site 3 expected
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {3}

    # Site 3 belongs to supplier 20
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {20}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_supplier_and_site(mock_db_env):
    q_params = {
            "supplier": "10",
            "site": "3"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)
    
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2, 3}
    
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]


# ------------------------------
# Multiple Sites and Suppliers Tests
# ------------------------------

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_multiple_sites(mock_db_env):
    q_params = {
            "site": "2,3,4"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Sites 2, 3, 4 expected
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {2, 3, 4}

    # Suppliers corresponding to those sites
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_multiple_suppliers(mock_db_env):
    q_params = {
            "supplier": "10,20"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Sites for supplier 10 and 20 are 1, 2, and 3
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2, 3}

    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_multiple_suppliers_and_sites(mock_db_env):
    q_params = {
            "supplier": "10,30",
            "site": "3,4"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Sites should include supplier 10's sites (1, 2) + sites 3,4 explicitly requested
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2, 3, 4}

    # Suppliers from these sites should be 10, 20, and 30
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]


# ------------------------------
# Repeated Site and Supplier Tests
# ------------------------------
@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_repeated_same_supplier(mock_db_env):
    q_params = {
            "supplier": "10,10,10"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Supplier 10 has sites 1 and 2, so these sites expected once
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2}

    assert 'id' in body[0]['supplier']
    assert 'name' in body[0]['supplier']
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

    assert len(body) == 2  # Only two unique sites, so two entries expected

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_repeated_same_site(mock_db_env):
    q_params = {
            "site": "3,3,3"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Only site 3 expected once
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {3}

    # Site 3 belongs to supplier 20
    assert 'id' in body[0]['supplier']
    assert 'name' in body[0]['supplier']
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {20}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

    assert len(body) == 1  # Only one unique site, so one entry expected

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_repeated_same_suppliers_and_sites(mock_db_env):
    q_params = {
            "supplier": "10,10,30,30",
            "site": "3,3,4,4"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Sites: supplier 10 has sites 1 and 2, plus explicitly requested sites 3 and 4
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2, 3, 4}

    # Suppliers should be 10, 20 (from site 3), and 30 (site 4)
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

    assert len(body) == 4  # Four unique combinations of site and supplier expected


# ------------------------------
# Invalid Site and Supplier Tests
# ------------------------------
@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_invalid_supplier_ids_and_one_legal(mock_db_env):
    q_params = {
            "supplier": "999,abc,-1,30"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Valid supplier 30, but 999 and -1 are invalid, 'abc' is not an int
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {4}  # Only site 4 belongs to supplier 30

    # Supplier 30 is the only valid supplier
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {30}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

    # Valid supplier 30, but 999 and -1 are invalid, 'abc' is not an int
    assert len(body) == 1

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_invalid_supplier_ids(mock_db_env):
    q_params = {
            "supplier": "999,abc,-1"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    assert len(body) == 0

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_invalid_site_ids_and_one_legal(mock_db_env):
    q_params = {
            "site": "999,xyz,-5,1"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Valid site 1, but 999 and -5 are invalid, 'xyz' is not an int
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1}  # Only site 1 is valid

    # Supplier for site 1 is 10
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

    # Valid site 1, but 999 and -5 are invalid, 'xyz' is not an int
    assert len(body) == 1

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_invalid_site_ids(mock_db_env):
    q_params = {
            "site": "999,xyz,-5"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    assert len(body) == 0

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_invalid_supplier_and_site_ids(mock_db_env):
    q_params = {
            "supplier": "999,notanint",
            "site": "abc,1000"
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # No valid suppliers or sites, no results expected
    assert len(body) == 0


# ------------------------------
# Empty Query String Parameters Tests
# ------------------------------
@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_empty_query_string_params(mock_db_env):
    q_params = {
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # No suppliers or sites specified, should return all sites and suppliers
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2, 3, 4}

    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

    assert len(body) == 4  # All sites


# ------------------------------
# No Query String Parameters Tests
# ------------------------------
@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_no_query_string_params(mock_db_env):
    q_params = {}

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # No suppliers or sites specified, should return all sites and suppliers
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2, 3, 4}

    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

    assert len(body) == 4


# ------------------------------
# Bad keys in query string parameters Tests
# ------------------------------
@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_bad_query_key_params(mock_db_env):
    q_params = {
            "invalid_key": "some_value",
            "another_invalid_key": "another_value",
            "site": "3",
    }

    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Only one site expected (3)
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {3}

    # Site 3 belongs to supplier 20
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {20}

    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]

    assert len(body) == 1  # Only one unique site, so one entry expected

# ------------------------------
# Additional Edge Cases Tests
# ------------------------------
@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_empty_supplier_and_site_values(mock_db_env):
    # Both supplier and site provided as empty strings
    q_params = {
            "supplier": "",
            "site": ""
    }
    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # With empty inputs, should return all sites from the database
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    
    assert site_ids == {1, 2, 3, 4}
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20, 30}
    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]
    assert len(body) == 4

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_supplier_with_whitespace_values(mock_db_env):
    # Supplier field with only whitespace should be treated as empty
    q_params = {
            "supplier": "   ",
            "site": "3"
    }
    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Only site is provided so it should return site 3 info
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {3}
    
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {20}
    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]
    assert len(body) == 1

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_site_with_whitespace_values(mock_db_env):
    # Site field with only whitespace should be treated as empty, thus returns all sites
    q_params = {
            "supplier": "10",
            "site": "    "
    }
    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Supplier 10 returns sites 1 and 2
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2}
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    
    assert supplier_ids == {10}
    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]
    assert len(body) == 2

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_supplier_trailing_comma(mock_db_env):
    # Trailing comma in supplier string
    q_params = {
            "supplier": "10,",
    }
    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Trailing comma should not add extra invalid entry; supplier 10 is valid
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2}

    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10}
    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]
    assert len(body) == 2

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_site_trailing_comma(mock_db_env):
    # Trailing comma in site string
    q_params = {
            "site": "3,",
    }
    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Trailing comma should not add an extra invalid site; only site 3 is valid
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {3}

    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {20}
    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]
    assert len(body) == 1

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_supplier_extra_delimiters(mock_db_env):
    # Extra delimiters in supplier string ("10,,20" should be parsed as two valid suppliers)
    q_params = {
            "supplier": "10,,20"
    }
    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Supplier 10 covers sites 1 and 2; supplier 20 covers site 3
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 2, 3}

    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20}
    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]
    assert len(body) == 3

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_site_extra_delimiters(mock_db_env):
    # Extra delimiters in site string ("1,,4" should be parsed as two valid sites)
    q_params = {
            "site": "1,,4"
    }
    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Site 1 (supplier 10) and site 4 (supplier 30) expected
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    assert site_ids == {1, 4}

    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 30}
    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]
    assert len(body) == 2

@pytest.mark.usefixtures("patch_connector")
def test_calculate_dispatch_time_supplier_mixed_valid_invalid_with_whitespace(mock_db_env):
    # Mixed valid and invalid supplier ids along with whitespace
    q_params = {
            "supplier": " 10 , abc , 20 , , -5 "
    }
    body = calculate_dispatch_time(q_params)
    assert isinstance(body, list)

    # Valid suppliers are 10 and 20.
    assert 'id' in body[0]['site']
    assert 'location' in body[0]['site']
    site_ids = {entry["site"]["id"] for entry in body}
    # Supplier 10 => sites 1 and 2; Supplier 20 => site 3
    assert site_ids == {1, 2, 3}

    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10, 20}
    for entry in body:
        assert "indicators" in entry
        assert "ADT" in entry["indicators"]
        assert "DDI" in entry["indicators"]
    assert len(body) == 3


def test_calculate_dispatch_time_db_exception(mocker, in_memory_db, mock_db_env):
    class ErrorConnector(ReadOnlyDBConnector):
        def __init__(self, _: str):
            self._SessionLocal = in_memory_db

        @contextlib.contextmanager
        def session_scope(self):
            session = self._SessionLocal()
            try:
                raise Exception("Database connection error")
                yield session
            finally:
                session.close()

    mocker.patch("service.db_utils.ReadOnlyDBConnector", new=ErrorConnector)

    q_params = {}

    with pytest.raises(Exception):
        calculate_dispatch_time(q_params)