import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from model.vertex import Base, Vertex, VertexType
from service.read_only_db_connector import ReadOnlyDBConnector
from model_service.vertex_service import get_vertices, get_vertex_by_id
from model_dto.q_params import VerticesQParamsKeys


class InMemoryReadOnlyDBConnector(ReadOnlyDBConnector):
    def __init__(self, engine):
        self._Session = scoped_session(sessionmaker(bind=engine))

    def session_scope(self):            # type: ignore
        class _SessionContext:
            def __enter__(inner_self):      # type: ignore
                inner_self.session = self._Session()
                return inner_self.session

            def __exit__(inner_self, exc_type, exc_val, exc_tb):        # type: ignore
                inner_self.session.close()
        return _SessionContext()


@pytest.fixture(scope="module")
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()
    session.add_all([
        Vertex(id=1, name="ALPHA", type=VertexType.SUPPLIER_SITE),
        Vertex(id=2, name="BETA", type=VertexType.MANUFACTURER),
        Vertex(id=3, name="LEIPZIG, DE", type=VertexType.INTERMEDIATE),
    ])
    session.commit()
    session.close()

    return engine


@pytest.fixture(autouse=True)
def override_db(monkeypatch, in_memory_db):
    connector = InMemoryReadOnlyDBConnector(in_memory_db)
    monkeypatch.setattr("model_service.vertex_service.get_read_only_db_connector", lambda : connector)


def test_get_vertices_by_type():
    q_params = {
        VerticesQParamsKeys.TYPE.value: "SUPPLIER_SITE"
    }
    results = get_vertices(q_params)
    assert len(results) == 1
    assert results[0]["name"] == "ALPHA"
    assert results[0]["type"] == "SUPPLIER_SITE"


def test_get_vertices_by_invalid_type():
    q_params = {
        VerticesQParamsKeys.TYPE.value: "UNKNOWN"
    }
    results = get_vertices(q_params)
    assert results == []


def test_get_vertices_empty_query_returns_all():
    q_params = {}
    results = get_vertices(q_params)
    assert len(results) == 3
    assert {v["name"] for v in results} == {"ALPHA", "BETA", "LEIPZIG, DE"}


def test_get_vertices_by_name_only_uses_resolver():
    fake_resolver = MagicMock()
    # Simulate resolution of one name
    fake_resolver.resolve.side_effect = lambda dto: MagicMock(vertex=Vertex(id=1, name="LEIPZIG, DE", type=VertexType.INTERMEDIATE))

    with patch("model_service.vertex_service._initialize_resolver", return_value=fake_resolver):
        q_params = {
            VerticesQParamsKeys.NAME.value: "LEIPZIG; DE"
        }
        results = get_vertices(q_params)

    assert len(results) == 1
    assert results[0]["name"] == "LEIPZIG, DE"
    assert results[0]["type"] == "INTERMEDIATE"
    fake_resolver.resolve.assert_called_once()


def test_get_vertices_by_name_and_type_uses_resolver():
    fake_resolver = MagicMock()
    # Simulate resolution of name+type
    fake_resolver.resolve.side_effect = lambda dto: MagicMock(vertex=Vertex(id=1, name="LEIPZIG, DE", type=VertexType.INTERMEDIATE))

    with patch("model_service.vertex_service._initialize_resolver", return_value=fake_resolver):
        q_params = {
            VerticesQParamsKeys.NAME.value: "LEIPZIG; DE",
            VerticesQParamsKeys.TYPE.value: "INTERMEDIATE"
        }
        results = get_vertices(q_params)

    assert len(results) == 1
    assert results[0]["name"] == "LEIPZIG, DE"
    assert results[0]["type"] == "INTERMEDIATE"
    fake_resolver.resolve.assert_called_once()


def test_get_vertex_by_id_success():
    result = get_vertex_by_id(1)
    assert result["id"] == 1
    assert result["name"] == "ALPHA"
    assert result["type"] == "SUPPLIER_SITE"


def test_get_vertex_by_id_not_found():
    with pytest.raises(Exception) as e:
        get_vertex_by_id(999)
    assert "Vertex with ID 999 not found" in str(e.value)
