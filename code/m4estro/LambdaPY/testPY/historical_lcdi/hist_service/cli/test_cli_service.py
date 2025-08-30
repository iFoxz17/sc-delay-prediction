import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import contextlib
import boto3

from model.base import Base
from model.carrier import Carrier

from hist_service.cli.cli_service import calculate_cli
from service.read_only_db_connector import ReadOnlyDBConnector

# --------------------------------------------------------------
# Setup
# --------------------------------------------------------------

@pytest.fixture(scope="function")
def in_memory_db():
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    yield SessionLocal
    engine.dispose()


@pytest.fixture(scope="function")
def seed_data(in_memory_db):
    session = in_memory_db()

    # Carriers
    carriers = [
        Carrier(name="ups", n_orders=100, n_losses=10),
        Carrier(name="fedex", n_orders=50, n_losses=5),
        Carrier(name="dhl", n_orders=10, n_losses=1),
        Carrier(name="Empty", n_orders=0, n_losses=0),  # No orders
    ]
    session.add_all(carriers)

    session.commit()
    session.close()


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

    mocker.patch("hist_service.cli.cli_service.get_read_only_db_connector", return_value=TestConnector("test"))

# --------------------------------------------------------------
# CLI Tests
# --------------------------------------------------------------

@pytest.mark.usefixtures("patch_connector")
def test_calculate_cli_no_carrier():
    q_params = {}
    body = calculate_cli(q_params)
    assert isinstance(body, list)
    assert len(body) == 3  # ups, B, C
    for entry in body:
        assert "carrier" in entry
        assert "id" in entry["carrier"]
        assert "name" in entry["carrier"]
        assert "indicators" in entry
        assert "CLI" in entry["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_cli_one_carrier():
    q_params = {"carrier_name": "ups"}
    body = calculate_cli(q_params)
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["carrier"]['name'] == "ups"
    assert "CLI" in body[0]["indicators"]


@pytest.mark.usefixtures("patch_connector")
def test_calculate_cli_multiple_carriers():
    q_params = {"carrier_name": "ups,dhl"}
    body = calculate_cli(q_params)
    names = {entry["carrier"]['name'] for entry in body}
    assert names == {"ups", "dhl"}


@pytest.mark.usefixtures("patch_connector")
def test_calculate_cli_invalid_carrier():
    q_params = {"carrier_name": "NonExistentCarrier"}
    body = calculate_cli(q_params)
    assert body == []

@pytest.mark.usefixtures("patch_connector")
def test_calculate_cli_valid_and_invalid_carrier():
    q_params = {"carrier_name": "fedex,nonexistant,   "}
    body = calculate_cli(q_params)
    names = {entry["carrier"]['name'] for entry in body}
    assert names == {"fedex"}

@pytest.mark.usefixtures("patch_connector")
def test_calculate_cli_upper_case_carrier():
    q_params = {"carrier_name": "FEDEX, uPs"}
    body = calculate_cli(q_params)
    names = {entry["carrier"]['name'] for entry in body}
    assert names == {"fedex", "ups"}
