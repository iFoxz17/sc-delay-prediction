import pytest
from unittest.mock import patch, MagicMock
import igraph as ig

from model.vertex import VertexType
from model.location import Location

from resolver.vertex_resolver import VertexResolver, VertexResult
from resolver.vertex_dto import VertexIdDTO, VertexNameDTO
from resolver.vertex_not_found_exception import (
    VertexIdNotFoundException,
    VertexNameNotFoundException,
    VertexNameTypeNotFoundException,
)
from service.lambda_client.geo_service_lambda_client import LocationResult, GeoServiceLambdaClient

@pytest.fixture
def simple_graph():
    g = ig.Graph(directed=True)
    g.add_vertex(name="MANUFACTURER_NAME", v_id=1, type=VertexType.MANUFACTURER.value)
    g.add_vertex(name="SUPPLIER1", v_id=2, type=VertexType.SUPPLIER_SITE.value)
    g.add_vertex(name="MILAN, LOMBARDY, IT", v_id=3, type=VertexType.INTERMEDIATE.value)
    return g

@pytest.fixture
def external_api_client():
    client = MagicMock(spec=GeoServiceLambdaClient)
    client.get_location_data.return_value = LocationResult(
        name="MILAN, LOMBARDY, IT",
        city="Milan",
        state="Lombardy",
        country="Italy",
        country_code="IT",
        latitude=45.4642,
        longitude=9.1900
    )
    return client

def test_resolve_vertex_by_id(simple_graph, external_api_client):
    dto = VertexIdDTO(vertexId=1)
    resolver = VertexResolver(graph=simple_graph, lambda_client=external_api_client)
    result = resolver.resolve(dto)

    assert isinstance(result.vertex, ig.Vertex)
    assert result.vertex["v_id"] == 1
    assert result.vertex["name"] == "MANUFACTURER_NAME"

def test_resolve_vertex_by_name(simple_graph, external_api_client):
    dto = VertexNameDTO(vertexName="SUPPLIER1")
    resolver = VertexResolver(graph=simple_graph, lambda_client=external_api_client)
    result = resolver.resolve(dto)

    assert isinstance(result.vertex, ig.Vertex)
    assert result.vertex["name"] == "SUPPLIER1"

def test_resolve_vertex_by_invalid_id(simple_graph, external_api_client):
    dto = VertexIdDTO(vertexId=999)
    resolver = VertexResolver(graph=simple_graph, lambda_client=external_api_client)

    with pytest.raises(VertexIdNotFoundException):
        resolver.resolve(dto)

def test_resolve_vertex_by_invalid_name(simple_graph, external_api_client):
    dto = VertexNameDTO(vertexName="Gamma")
    resolver = VertexResolver(graph=simple_graph, lambda_client=external_api_client)

    with pytest.raises(VertexNameNotFoundException):
        resolver.resolve(dto)

@patch("resolver.vertex_resolver.get_db_connector")
def test_resolve_vertex_by_name_and_type_intermediate_external_api_lookup(
    mock_get_db_connector, simple_graph, external_api_client
):
    # Setup DBConnector mock
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_connector = MagicMock()
    mock_connector.session_scope.return_value.__enter__.return_value = mock_session
    mock_get_db_connector.return_value = mock_connector

    dto = VertexNameDTO(vertexName="Milan, Italy", vertexType=VertexType.INTERMEDIATE)
    resolver = VertexResolver(graph=simple_graph, lambda_client=external_api_client)
    result = resolver.resolve(dto)

    assert isinstance(result.vertex, ig.Vertex)
    assert result.vertex["name"] == "MILAN, LOMBARDY, IT"
    assert result.vertex["type"] == VertexType.INTERMEDIATE.value

@patch("resolver.vertex_resolver.get_db_connector")
def test_resolve_vertex_by_name_and_type_intermediate_no_country_external_api_lookup(
    mock_get_db_connector, simple_graph, external_api_client
):
    # Setup DBConnector mock
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_connector = MagicMock()
    mock_connector.session_scope.return_value.__enter__.return_value = mock_session
    mock_get_db_connector.return_value = mock_connector

    dto = VertexNameDTO(vertexName="Milan", vertexType=VertexType.INTERMEDIATE)
    resolver = VertexResolver(graph=simple_graph, lambda_client=external_api_client)
    result = resolver.resolve(dto)

    assert isinstance(result.vertex, ig.Vertex)
    assert result.vertex["name"] == "MILAN, LOMBARDY, IT"
    assert result.vertex["type"] == VertexType.INTERMEDIATE.value

@patch("resolver.vertex_resolver.get_db_connector")
def test_resolve_vertex_by_name_and_type_intermediate_db_lookup(
    mock_get_db_connector, simple_graph, external_api_client
):
    # Setup DBConnector mock
    mock_session = MagicMock()
    location: Location = Location(
        id=1,
        name="MILAN, LOMBARDY, IT",
        city="Milan",
        state="Lombardy",
        country_code="IT",
        latitude=45.4642,
        longitude=9.1900
    )
    mock_query = MagicMock()
    # The filter calls return the same mock query for chaining
    mock_query.filter.return_value = mock_query

    # The all() call returns your desired list
    mock_query.all.return_value = [location]

    mock_session.query.return_value = mock_query
    mock_connector = MagicMock()
    mock_connector.session_scope.return_value.__enter__.return_value = mock_session
    mock_get_db_connector.return_value = mock_connector

    dto = VertexNameDTO(vertexName="Milan, Italy", vertexType=VertexType.INTERMEDIATE)
    resolver = VertexResolver(graph=simple_graph, lambda_client=external_api_client)
    result = resolver.resolve(dto)

    assert isinstance(result.vertex, ig.Vertex)
    assert result.vertex["name"] == "MILAN, LOMBARDY, IT"
    assert result.vertex["type"] == VertexType.INTERMEDIATE.value

@patch("resolver.vertex_resolver.get_db_connector")
def test_resolve_vertex_by_name_and_type_intermediate_no_country_db_lookup(mock_get_db_connector, simple_graph, external_api_client):
    # Setup DBConnector mock
    mock_session = MagicMock()
    location: Location = Location(
        id=1,
        name="MILAN, LOMBARDY, IT",
        city="Milan",
        state="Lombardy",
        country_code="IT",
        latitude=45.4642,
        longitude=9.1900
    )
    mock_query = MagicMock()
    # The filter calls return the same mock query for chaining
    mock_query.filter.return_value = mock_query

    # The all() call returns your desired list
    mock_query.all.return_value = [location]

    mock_session.query.return_value = mock_query
    mock_connector = MagicMock()
    mock_connector.session_scope.return_value.__enter__.return_value = mock_session
    mock_get_db_connector.return_value = mock_connector

    dto = VertexNameDTO(vertexName="Milan", vertexType=VertexType.INTERMEDIATE)
    resolver = VertexResolver(graph=simple_graph, lambda_client=external_api_client)
    result = resolver.resolve(dto)

    assert isinstance(result.vertex, ig.Vertex)
    assert result.vertex["name"] == "MILAN, LOMBARDY, IT"
    assert result.vertex["type"] == VertexType.INTERMEDIATE.value


def test_resolve_vertex_by_supplier_site_raises(simple_graph, external_api_client):
    dto = VertexNameDTO(vertexName="Supplier A", vertexType=VertexType.SUPPLIER_SITE)
    resolver = VertexResolver(graph=simple_graph, lambda_client=external_api_client)

    with pytest.raises(VertexNameTypeNotFoundException):
        resolver.resolve(dto)
