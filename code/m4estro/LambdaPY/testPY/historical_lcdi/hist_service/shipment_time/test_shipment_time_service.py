import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import contextlib
from contextlib import contextmanager

import boto3

from model.base import Base
from model.country import Country
from model.location import Location
from model.site import Site
from model.supplier import Supplier
from model.carrier import Carrier
from model.shipment_time_gamma import ShipmentTimeGamma
from model.shipment_time_sample import ShipmentTimeSample
from model.shipment_time import ShipmentTime
from model.param import Param, ParamName, ParamCategory, ParamGeneralCategory

from hist_service.shipment_time.shipment_time_service import calculate_shipment_time
from service.read_only_db_connector import ReadOnlyDBConnector

# --------------------------------------------------------------
# Setup fixtures
# --------------------------------------------------------------

@pytest.fixture(scope="function")
def in_memory_db():
    """
    Create an in-memory SQLite database and return a Session factory.
    """
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    yield SessionLocal
    engine.dispose()


@pytest.fixture(scope="function")
def seed_data(in_memory_db):
    """
    Seed the in-memory database with countries, locations, suppliers, carriers,
    sites, and shipment-time (gamma & sample) records.
    """
    session = in_memory_db()

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
    ]
    session.add_all(locations)
    session.commit()

    # --- Suppliers ---
    supplier1 = Supplier(id=10, manufacturer_supplier_id=1, name="Supplier A")
    supplier2 = Supplier(id=20, manufacturer_supplier_id=2, name="Supplier B")
    supplier3 = Supplier(id=30, manufacturer_supplier_id=3, name="Supplier C")
    session.add_all([supplier1, supplier2, supplier3])
    session.commit()

    # --- Carriers ---
    dhl = Carrier(name="dhl", carrier_17track_id="10000", n_orders=50, n_losses=5)
    fedex = Carrier(name="fedex", carrier_17track_id="20000", n_orders=30, n_losses=3)
    ups = Carrier(name="ups", carrier_17track_id="30000", n_orders=80, n_losses=8)
    session.add_all([dhl, fedex, ups])
    session.commit()

    # --- Sites ---
    site1 = Site(id=1, supplier_id=10, location_name="Location A", n_rejections=5, n_orders=100)
    site2 = Site(id=2, supplier_id=10, location=locations[1], n_rejections=3, n_orders=80)
    site3 = Site(id=3, supplier_id=20, location_name="Location C", n_rejections=2, n_orders=18)
    site4 = Site(id=4, supplier_id=30, location=locations[3], n_rejections=1, n_orders=12)
    site5 = Site(id=5, supplier_id=20, location_name="Location D", n_rejections=0, n_orders=0)
    session.add_all([site1, site2, site3, site4, site5])
    session.commit()

    # --- ShipmentTime (raw samples) ---
    # site 1: dhl twice, fedex once
    dt1 = ShipmentTime(site_id=1, carrier=dhl, hours=2.5)
    dt2 = ShipmentTime(site_id=1, carrier=fedex, hours=3.0)
    dt3 = ShipmentTime(site_id=1, carrier=fedex, hours=1.5)
    # site 2: dhl once, ups twice
    dt4 = ShipmentTime(site_id=2, carrier=dhl, hours=4.0)
    dt5 = ShipmentTime(site_id=2, carrier=ups, hours=2.0)
    dt6 = ShipmentTime(site_id=2, carrier=ups, hours=3.5)
    # site 3: ups twice
    dt7 = ShipmentTime(site_id=3, carrier=ups, hours=1.0)
    dt8 = ShipmentTime(site_id=3, carrier=ups, hours=4.5)
    # site 4: fedex once, dhl once
    dt9 = ShipmentTime(site_id=4, carrier=fedex, hours=2.2)
    dt10 = ShipmentTime(site_id=4, carrier=dhl, hours=3.2)
    session.add_all([dt1, dt2, dt3, dt4, dt5, dt6, dt7, dt8, dt9, dt10])
    session.commit()

    # --- ShipmentTimeGamma & ShipmentTimeSample ---
    # Site 1:
    gamma1A = ShipmentTimeGamma(
        id=1,
        site_id=1,
        carrier=dhl,
        shape=1.0,
        loc=0.5,
        scale=2.0,
        skewness=0.1,
        kurtosis=3.0,
        mean=5.0,
        std_dev=1.5,
        n=100
    )
    sample1B = ShipmentTimeSample(
        id=1,
        site_id=1,
        carrier=fedex,
        median=3.4,
        mean=4.0,
        std_dev=1.2,
        n=18,
    )

    # Site 2:
    gamma2C = ShipmentTimeGamma(
        id=2,
        site_id=2,
        carrier=ups,
        shape=2.0,
        loc=1.5,
        scale=3.0,
        skewness=0.2,
        kurtosis=4.0,
        mean=6.0,
        std_dev=1.8,
        n=80
    )
    sample2A = ShipmentTimeSample(
        id=2,
        site_id=2,
        carrier=dhl,
        median=3.1,
        mean=6.0,
        std_dev=1.98,
        n=12,
    )

    # Site 3:
    sample3C = ShipmentTimeSample(
        id=3,
        site_id=3,
        carrier=ups,
        median=3.123,
        mean=6.8,
        std_dev=1.9823,
        n=14,
    )

    # Site 4:
    sample4A = ShipmentTimeSample(
        id=4,
        site_id=4,
        carrier=dhl,
        median=1.123,
        mean=2.8,
        std_dev=3.9823,
        n=10,
    )
    sample4B = ShipmentTimeSample(
        id=5,
        site_id=4,
        carrier=fedex,
        median=5.123,
        mean=9.8,
        std_dev=12.9823,
        n=19,
    )

    session.add_all([gamma1A, sample1B, gamma2C, sample2A, sample3C, sample4A, sample4B])
    session.commit()

    cl = Param(name=ParamName.SHIPMENT_HIST_CONFIDENCE.value, 
               general_category=ParamGeneralCategory.HISTORICAL.value,
               category=ParamCategory.SHIPMENT_TIME.value,
               value=0.95, 
               description="Confidence level for shipment time calculations")
    
    session.add(cl)
    session.commit()

    session.close()


@pytest.fixture(scope="function")
def patch_connector(in_memory_db, seed_data, mocker):
    """
    Monkey‐patch ReadOnlyDBConnector so that calculate_shipment_time() uses our in‐memory DB.
    """
    class TestConnector(ReadOnlyDBConnector):
        def __init__(self, _: str):
            self._SessionLocal = in_memory_db

        @contextmanager
        def session_scope(self):
            session = self._SessionLocal()
            try:
                yield session
            finally:
                session.close()

    mocker.patch("service.db_utils.ReadOnlyDBConnector", new=TestConnector)


@pytest.fixture(scope="function")
def mock_db_env(monkeypatch):
    """
    Monkey‐patch the AWS secrets (so that get_db_credentials + build_connection_url succeed).
    We return a dummy JSON in get_secret_value.
    """
    database_secret_arn = "sqlite:///:memory:"
    region = "eu-west-1"

    monkeypatch.setenv("DATABASE_SECRET_ARN", database_secret_arn)
    monkeypatch.setenv("AWS_REGION", region)

    dummy_creds = json.dumps({
        "username": "mockuser",
        "password": "mockpass",
        "host":     "mockhost",
        "port":     5432,
        "dbname":   "mockdb"
    })

    class MockClient:
        def get_secret_value(self, SecretId):
            return {"SecretString": dummy_creds}

    monkeypatch.setattr(
        boto3,
        "client",
        lambda service_name, region_name=None: MockClient()
    )


# --------------------------------------------------------------
# Tests (site + supplier + carrier logic)
# --------------------------------------------------------------

@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_only_supplier(mock_db_env):
    q_params = {"supplier": "10"}

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # Supplier 10 covers:
    #   site 1: dhl (gamma), fedex (sample)
    #   site 2: dhl (sample), ups (gamma)
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups")
    }
    assert "id" in body[0]["site"]
    assert "location" in body[0]["site"]
    assert {(entry["site"]["id"], entry["carrier"]['name']) for entry in body} == expected_pairs

    assert "id" in body[0]["supplier"]
    assert "name" in body[0]["supplier"]
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10}

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_only_carrier(mock_db_env):
    q_params = {
        "carrier_name": "ups"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # UPS is used at site 2 (gamma), site 3 (sample)
    expected_pairs = {(2, "ups"), (3, "ups")}
    assert {(entry["site"]["id"], entry["carrier"]['name']) for entry in body} == expected_pairs

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_only_site(mock_db_env):
    q_params = {
        "site": "3"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # Only site 3 → ups (sample)
    assert len(body) == 1
    assert {(entry["site"]["id"], entry["carrier"]['name']) for entry in body} == {(3, "ups")}

    # site 3 → supplier 20
    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {20}

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_supplier_and_site(mock_db_env):
    q_params = {
            "supplier": "10",
            "site": "3"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # supplier=10 → sites {1,2}; plus site=3 → {1,2,3}
    # site1: dhl, fedex
    # site2: dhl, ups
    # site3: ups
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups")
    }

    assert "id" in body[0]["site"]
    assert "location" in body[0]["site"]
    assert {(e["site"]["id"], e["carrier"]['name']) for e in body} == expected_pairs

    assert "id" in body[0]["supplier"]
    assert "name" in body[0]["supplier"]
    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20}

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_site_and_carrier(mock_db_env):
    q_params = {
            "site": "1",
            "carrier_name": "fedex"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # site 1 + fedex → sample only
    assert len(body) == 1
    assert body[0]["site"]['id'] == 1
    assert 'location' in body[0]["site"]
    assert body[0]["carrier"]['name'] == "fedex"
    assert body[0]["supplier"]['id'] == 10
    assert 'name' in body[0]["supplier"]

    assert "AST" in body[0]["indicators"]
    assert "CTDI" in body[0]["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_supplier_and_carrier(mock_db_env):
    q_params = {
            "supplier": "10",
            "carrier_name": "dhl"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # Supplier 10: site 1 and 2 → check only dhl
    # site1: dhl (gamma)
    # site2: dhl (sample)
    expected_pairs = {(1, "dhl"), (2, "dhl")}
    assert {(entry["site"]["id"], entry["carrier"]['name']) for entry in body} == expected_pairs

    supplier_ids = {entry["supplier"]["id"] for entry in body}
    assert supplier_ids == {10}

    for entry in body:
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_supplier_site_carrier(mock_db_env):
    q_params = {
            "supplier": "10",
            "site": "3",
            "carrier_name": "dhl"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # site 1, supplier 10, carrier dhl → gamma
    assert len(body) == 2
    for entry in body:
        assert entry["site"]["id"] == 3 or entry["supplier"]["id"] == 10
        assert entry["carrier"]['name'] == "dhl"
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_multiple_sites(mock_db_env):
    q_params = {
        "site": "2,3,4"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # site2: dhl (sample), ups (gamma)
    # site3: ups (sample)
    # site4: dhl (sample), fedex (sample)
    expected_pairs = {
        (2, "dhl"), (2, "ups"),
        (3, "ups"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]['name']) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_multiple_suppliers(mock_db_env):
    q_params = {
        "supplier": "10,20"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # supplier=10 → site1: (dhl, fedex), site2: (dhl, ups)
    # supplier=20 → site3: (ups)
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups")
    }
    assert {(e["site"]["id"], e["carrier"]['name']) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20}

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_multiple_carriers(mock_db_env):
    q_params = {
        "carrier_name": "dhl,ups"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # dhl → site 1 (gamma), site 2 (sample), site 4 (sample)
    # ups → site 2 (gamma), site 3 (sample)
    expected_pairs = {
        (1, "dhl"), (2, "dhl"), (4, "dhl"),
        (2, "ups"), (3, "ups")
    }
    assert {(e["site"]["id"], e["carrier"]['name']) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_multiple_suppliers_and_sites(mock_db_env):
    q_params = {
        "supplier": "10,30",
        "site": "3,4"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # supplier=10 → site1: (dhl, fedex), site2: (dhl, ups)
    # site 3 → (ups)
    # site 4 → (dhl, fedex)
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]['name']) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    # site3→supplier20, site4→supplier30
    assert supplier_ids == {10, 20, 30}

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_multiple_sites_and_carriers(mock_db_env):
    q_params = {
        "site": "1,4",
        "carrier_name": "dhl,fedex"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]['name']) for e in body} == expected_pairs

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_multiple_suppliers_and_carriers(mock_db_env):
    q_params = {
            "supplier": "10,30",
            "carrier_name": "fedex,ups"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # supplier 10: site1 (fedex), site2 (ups)
    # supplier 30: site4 (fedex)
    expected_pairs = {
        (1, "fedex"), (2, "ups"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 30}

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_multiple_sites_carriers_suppliers(mock_db_env):
    q_params = {
            "supplier": "10,20",
            "site": "2,3",
            "carrier_name": "dhl,ups"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # supplier 10: site2 (dhl, ups)
    # supplier 20: site3 (ups)
    expected_pairs = {
        (1, "dhl"), (2, "ups"), (2, "dhl"), (3, "ups")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20}

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_repeated_same_supplier(mock_db_env):
    q_params = {
            "supplier": "10,10,10"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # Only supplier=10 → 
    #   site1: (dhl, fedex), site2: (dhl, ups)
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10}
    assert len(body) == 4


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_repeated_same_carrier(mock_db_env):
    q_params = {
            "carrier_name": "ups,ups,ups"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # ups → site 2 (gamma), site 3 (sample)
    expected_pairs = {(2, "ups"), (3, "ups")}
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20}


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_repeated_same_site(mock_db_env):
    q_params = {
            "site": "3,3,3"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # Only site3 → (ups)
    assert len(body) == 1
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == {(3, "ups")}

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {20}


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_repeated_same_suppliers_and_sites(mock_db_env):
    q_params = {
            "supplier": "10,10,30,30",
            "site": "3,3,4,4"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # supplier=10 → site1: (dhl, fedex), site2: (dhl, ups)
    # site3 → (ups), site4 → (dhl, fedex)
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20, 30}
    assert len(body) == 7  # four from supplier=10 plus one for site3 plus two for site4


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_mixed_unique_and_repeated_carriers(mock_db_env):
    q_params = {
            "carrier_name": "ups,dhl,dhl,ups"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # dhl → site 1 (gamma), site 2 (sample), site 4 (sample)
    # ups → site 2 (gamma), site 3 (sample)
    expected_pairs = {
        (1, "dhl"), (2, "dhl"), (4, "dhl"),
        (2, "ups"), (3, "ups")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20, 30}


# --------------------------------------------------------------
# Tests for invalid inputs (supplier + site + carrier)
# --------------------------------------------------------------

@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_invalid_supplier_ids_and_one_legal(mock_db_env):
    q_params = {
            "supplier": "999,abc,-1,30"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # Only supplier=30 is valid → site=4 → carriers for site4: (dhl, fedex)
    expected_pairs = {(4, "dhl"), (4, "fedex")}
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {30}
    assert len(body) == 2


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_invalid_supplier_ids(mock_db_env):
    q_params = {
            "supplier": "999,abc,-1"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)
    assert len(body) == 0  # no valid supplier → no results


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_invalid_site_ids_and_one_legal(mock_db_env):
    q_params = {
            "site": "999,xyz,-5,1"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # Only site=1 is valid → carriers: (dhl, fedex)
    expected_pairs = {(1, "dhl"), (1, "fedex")}
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10}
    assert len(body) == 2


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_invalid_site_ids(mock_db_env):
    q_params = {
            "site": "999,xyz,-5"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)
    assert len(body) == 0


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_invalid_carrier_and_one_legal(mock_db_env):
    q_params = {
            "carrier_name": "xyz,none,ups"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # UPS is used at site 2 (supplier 10), site 3 (supplier 20)
    expected_pairs = {(2, "ups"), (3, "ups")}
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    carrier_names = {e["carrier"]["name"] for e in body}
    assert carrier_names == {"ups"}


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_invalid_carrier_only(mock_db_env):
    q_params = {
            "carrier_name": "xxx,-1,999"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)
    assert len(body) == 0  # no valid carriers → no results


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_invalid_supplier_site_carrier_and_one_valid_each(mock_db_env):
    q_params = {
            "supplier": "junk,10",
            "site": "999,1",
            "carrier_name": "bad,dhl"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # supplier 10 → site 1 → carriers: dhl, fedex → only dhl matches
    expected_pairs = {(1, "dhl"), (2, "dhl")}
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["supplier"]["id"] for e in body} == {10}
    assert {e["carrier"]["name"] for e in body} == {"dhl"}


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_all_invalid_supplier_site_carrier(mock_db_env):
    q_params = {
            "supplier": "zzz",
            "site": "none",
            "carrier_name": "oops"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)
    assert len(body) == 0  # all invalid → no results


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_valid_supplier_carrier_invalid_site(mock_db_env):
    q_params = {
            "supplier": "10",
            "site": "999",
            "carrier_name": "fedex"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # supplier 10 → site 1 & 2 → site filter is invalid, so no site matches
    assert len(body) == 1
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == {(1, "fedex")}
    assert {e["supplier"]["id"] for e in body} == {10}


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_valid_site_carrier_invalid_supplier(mock_db_env):
    q_params = {
            "supplier": "999",
            "site": "1",
            "carrier_name": "dhl"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    assert len(body) == 1
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == {(1, "dhl")}


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_valid_site_supplier_invalid_carrier(mock_db_env):
    q_params = {
            "supplier": "10",
            "site": "1",
            "carrier_name": "ghost"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # site 1 (supplier 10) has dhl, fedex → ghost is invalid
    assert len(body) == 0


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_mixed_duplicates_invalids(mock_db_env):
    q_params = {
            "supplier": "10,10,999",
            "site": "1,1,abc",
            "carrier_name": "dhl,dhl,none"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    expected_pairs = {(1, "dhl"), (2, "dhl")}
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["supplier"]["id"] for e in body} == {10}


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_invalid_supplier_and_site_ids(mock_db_env):
    q_params = {
            "supplier": "999,notanint",
            "site": "abc,1000"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)
    assert len(body) == 0  # no valid suppliers or sites → no results


# --------------------------------------------------------------
# Tests for empty or missing query params
# --------------------------------------------------------------

@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_empty_query_string_params(mock_db_env):
    q_params = {}

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # No filters → return every (site, carrier) combination present:
    #   site1: (dhl, fedex)
    #   site2: (dhl, ups)
    #   site3: (ups)
    #   site4: (dhl, fedex)
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20, 30}
    assert len(body) == 7


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_no_query_string_params(mock_db_env):
    q_params = {}

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs

    supplier_ids = {e["supplier"]["id"] for e in body}
    assert supplier_ids == {10, 20, 30}
    assert len(body) == 7


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_bad_query_key_params(mock_db_env):
    q_params = {
            "invalid_key": "foo",
            "another_invalid_key": "bar",
            "site": "3"
    }

    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # Only site 3 → (ups)
    assert len(body) == 1
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == {(3, "ups")}
    assert {e["supplier"]["id"] for e in body} == {20}


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_empty_supplier_and_site_values(mock_db_env):
    q_params = {
            "supplier": "",
            "site": ""
    }
    body = calculate_shipment_time(q_params)

    # Equivalent to no filters → same as empty querystring → 7 entries total
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["supplier"]["id"] for e in body} == {10, 20, 30}
    assert len(body) == 7


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_empty_supplier_site_carrier_values(mock_db_env):
    q_params = {
            "supplier": "",
            "site": "",
            "carrier_name": ""
    }
    body = calculate_shipment_time(q_params)

    # Equivalent to no filters → same as empty querystring → 7 entries total
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["supplier"]["id"] for e in body} == {10, 20, 30}
    assert len(body) == 7


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_supplier_with_whitespace_values(mock_db_env):
    q_params = {
            "supplier": "   ",
            "site": "3"
    }
    body = calculate_shipment_time(q_params)

    # Only site=3 → (ups)
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == {(3, "ups")}
    assert {e["supplier"]["id"] for e in body} == {20}
    assert len(body) == 1


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_site_with_whitespace_values(mock_db_env):
    q_params = {
            "supplier": "10",
            "site": "    "
    }
    body = calculate_shipment_time(q_params)

    # supplier=10 → site1: (dhl, fedex), site2: (dhl, ups)
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["supplier"]["id"] for e in body} == {10}
    assert len(body) == 4


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_supplier_trailing_comma(mock_db_env):
    q_params = {
            "supplier": "10,"
    }
    body = calculate_shipment_time(q_params)

    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["supplier"]["id"] for e in body} == {10}
    assert len(body) == 4


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_site_trailing_comma(mock_db_env):
    q_params = {
            "site": "3,"
    }
    body = calculate_shipment_time(q_params)

    # Only (3,ups)
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == {(3, "ups")}
    assert {e["supplier"]["id"] for e in body} == {20}
    assert len(body) == 1


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_supplier_extra_delimiters(mock_db_env):
    q_params = {
            "supplier": "10,,20"
    }

    body = calculate_shipment_time(q_params)

    # supplier=10 → site1: (dhl,fedex), site2: (dhl,ups)
    # supplier=20 → site3: (ups)
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["supplier"]["id"] for e in body} == {10, 20}
    assert len(body) == 5


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_invalid_carrier_values(mock_db_env):
    q_params = {
            "carrier_name": "invalid,123,-ups"
    }
    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)
    assert len(body) == 0  # No valid carriers → no results


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_one_valid_carrier_among_invalid(mock_db_env):
    q_params = {
            "carrier_name": "notacarrier,,fedex,!!"
    }
    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # fedex is valid → found in sites 1 and 4 (supplier=10, 30)
    expected_pairs = {(1, "fedex"), (4, "fedex")}
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["carrier"]["name"] for e in body} == {"fedex"}
    assert {e["supplier"]["id"] for e in body} == {10, 30}
    assert len(body) == 2


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_carrier_with_whitespace(mock_db_env):
    q_params = {
            "carrier_name": "   "
    }
    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)
    assert len(body) == 0  # Whitespace only → no valid carriers


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_carrier_trailing_comma(mock_db_env):
    q_params = {
            "carrier_name": "dhl,"
    }
    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # dhl is valid → sites 1, 2, 4
    expected_pairs = {(1, "dhl"), (2, "dhl"), (4, "dhl")}
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["carrier"]["name"] for e in body} == {"dhl"}
    assert {e["supplier"]["id"] for e in body} == {10, 30}
    assert len(body) == 3


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_carrier_extra_delimiters(mock_db_env):
    q_params = {
            "carrier_name": "ups,,fedex"
    }
    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # ups: sites 2 (supplier 10), 3 (supplier 20)
    # fedex: sites 1 (supplier 10), 4 (supplier 30)
    expected_pairs = {
        (1, "fedex"), (2, "ups"),
        (3, "ups"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["carrier"]["name"] for e in body} == {"ups", "fedex"}
    assert {e["supplier"]["id"] for e in body} == {10, 20, 30}
    assert len(body) == 4


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_carrier_mixed_valid_invalid_with_whitespace(mock_db_env):
    q_params = {
            "carrier_name": " ups , notvalid , fedex , , DHL "
        }
    body = calculate_shipment_time(q_params)
    assert isinstance(body, list)

    # ups: site2 (10), site3 (20)
    # fedex: site1 (10), site4 (30)
    # dhl: site1 (10), site2 (10), site4 (30)
    expected_pairs = {
        (1, "fedex"), (1, "dhl"),
        (2, "dhl"), (2, "ups"),
        (3, "ups"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["carrier"]["name"] for e in body} == {"ups", "fedex", "dhl"}
    assert {e["supplier"]["id"] for e in body} == {10, 20, 30}
    assert len(body) == 7



@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_site_extra_delimiters(mock_db_env):
    q_params = {
            "site": "1,,4"
    }
    body = calculate_shipment_time(q_params)

    # Only (1,dhl),(1,fedex),(4,dhl),(4,fedex)
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (4, "dhl"), (4, "fedex")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["supplier"]["id"] for e in body} == {10, 30}
    assert len(body) == 4


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_supplier_mixed_valid_invalid_with_whitespace(mock_db_env):
    q_params = {
            "supplier": " 10 , abc , 20 , , -5 "
    }
    body = calculate_shipment_time(q_params)

    # Valid suppliers: 10 → site1 & site2 combos; 20 → site3 combo
    expected_pairs = {
        (1, "dhl"), (1, "fedex"),
        (2, "dhl"), (2, "ups"),
        (3, "ups")
    }
    assert {(e["site"]["id"], e["carrier"]["name"]) for e in body} == expected_pairs
    assert {e["supplier"]["id"] for e in body} == {10, 20}
    assert len(body) == 5


def test_shipment_time_db_exception(mocker, in_memory_db, mock_db_env):
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
        calculate_shipment_time(q_params)


@pytest.mark.usefixtures("patch_connector")
def test_calculate_shipment_time_carrier_with_invalid_and_valid_names(mock_db_env):
    """
    Mixed input "dhl,Nope,ups". Only dhl and ups are valid:
      - dhl: (1,dhl), (2,dhl), (4,dhl)
      - ups: (2,ups), (3,ups)
    """
    q_params = {
            "carrier_name": "dhl,Nope,ups"
    }
    body = calculate_shipment_time(q_params)

    assert 'id' in body[0]["site"]
    assert 'location' in body[0]["site"]
    expected_pairs = {
        (1, "dhl"), (2, "dhl"), (4, "dhl"),
        (2, "ups"), (3, "ups")
    }
    assert {(e["site"]['id'], e["carrier"]["name"]) for e in body} == expected_pairs

    assert 'id' in body[0]["supplier"]
    assert 'name' in body[0]["supplier"]
    # site1→10, site2→10, site3→20, site4→30
    assert {e["supplier"]["id"] for e in body} == {10, 20, 30}
    assert len(body) == 5

    for entry in body:
        assert "indicators" in entry
        assert "AST" in entry["indicators"]
        assert "CTDI" in entry["indicators"]
