import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from service.read_only_db_connector import ReadOnlyDBConnector

Base = declarative_base()

# Dummy ORM class for testing
class DummyModel(Base):
    __tablename__ = 'dummy'
    id = Column(Integer, primary_key=True)
    name = Column(String)

@pytest.fixture
def db_url():
    # Use in-memory SQLite for testing
    return "sqlite+pysqlite:///:memory:"

@pytest.fixture
def setup_db(db_url):
    connector = ReadOnlyDBConnector(db_url)
    # Create tables
    with connector.session_scope() as session:
        Base.metadata.create_all(bind=connector._engine)
        session.execute(
            DummyModel.__table__.insert(),
            [{"name": "Alice"}, {"name": "Bob"}]
        )
        session.commit()  # Temporary write for test seeding
    yield connector

    # Cleanup
    connector.dispose()

def test_read_only_session(setup_db):
    connector = setup_db

    with connector.session_scope() as session:
        results = session.query(DummyModel).all()
        assert len(results) == 2
        assert results[0].name == "Alice"
        assert results[1].name == "Bob"
