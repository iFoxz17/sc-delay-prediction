import pytest
from sqlalchemy import text
from service.db_connector import DBConnector

@pytest.fixture
def db_connector():
    # Use in-memory SQLite for testing
    connector = DBConnector("sqlite+pysqlite:///:memory:")
    # Create a simple test table to run queries against
    with connector.session_scope() as session:
        session.execute(text("CREATE TABLE test_table (id INTEGER PRIMARY KEY, val TEXT)"))
    yield connector

    # Cleanup
    connector.dispose()

def test_session_scope_commit(db_connector):
    with db_connector.session_scope() as session:
        session.execute(text("INSERT INTO test_table (val) VALUES ('test1')"))
        # No explicit commit needed, session_scope commits automatically

    # Verify the row was committed
    with db_connector.session_scope() as session:
        result = session.execute(text("SELECT val FROM test_table WHERE val='test1'")).fetchone()
        assert result is not None
        assert result[0] == 'test1'

def test_session_scope_rollback(db_connector):
    try:
        with db_connector.session_scope() as session:
            session.execute(text("INSERT INTO test_table (val) VALUES ('test2')"))
            raise RuntimeError("Force rollback")
    except RuntimeError:
        pass

    # Verify rollback: 'test2' should not be present
    with db_connector.session_scope() as session:
        result = session.execute(text("SELECT val FROM test_table WHERE val='test2'")).fetchone()
        assert result is None
