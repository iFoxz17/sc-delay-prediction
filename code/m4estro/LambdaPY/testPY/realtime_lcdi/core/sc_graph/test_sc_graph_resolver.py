import pytest
from unittest.mock import MagicMock, patch

from service.lambda_client.geo_service_lambda_client import GeoServiceLambdaClient

from resolver.vertex_dto import VertexDTO
from resolver.vertex_resolver import VertexResult
from core.sc_graph.sc_graph_resolver import SCGraphResolver, SCGraphVertexResult
from core.sc_graph.sc_graph import SCGraph


def test_init_with_provided_sc_graph():
    mock_graph = MagicMock()
    mock_sc_graph = MagicMock(spec=SCGraph)
    mock_sc_graph.graph = mock_graph

    mock_lambda_client = MagicMock(spec=GeoServiceLambdaClient)

    resolver = SCGraphResolver(lambda_client=mock_lambda_client, maybe_sc_graph=mock_sc_graph)

    assert resolver.graph is not None
    assert resolver.lambda_client is not None
    assert resolver.graph == mock_graph
    assert resolver.lambda_client == mock_lambda_client


@patch("core.sc_graph.sc_graph_resolver.BucketDataLoader")
def test_init_without_provided_sc_graph(mock_bucket_loader_class):
    mock_graph = MagicMock()
    mock_sc_graph = MagicMock(spec=SCGraph)
    mock_sc_graph.graph = mock_graph

    mock_loader_instance = MagicMock()
    mock_loader_instance.load_sc_graph.return_value = mock_sc_graph
    mock_bucket_loader_class.return_value = mock_loader_instance

    mock_lambda_client = MagicMock(spec=GeoServiceLambdaClient)

    resolver = SCGraphResolver(lambda_client=mock_lambda_client)

    mock_bucket_loader_class.assert_called_once()
    mock_loader_instance.load_sc_graph.assert_called_once()
    assert resolver.graph == mock_graph


@patch("core.sc_graph.sc_graph_resolver.VertexResolver.resolve")
def test_resolve_returns_wrapped_result(mock_super_resolve):
    mock_vertex_dto = MagicMock(spec=VertexDTO)
    mock_vertex = MagicMock()
    vertex_result = VertexResult(vertex=mock_vertex)

    mock_super_resolve.return_value = vertex_result

    mock_graph = MagicMock()
    mock_sc_graph = MagicMock(spec=SCGraph)
    mock_sc_graph.graph = mock_graph

    mock_lambda_client = MagicMock(spec=GeoServiceLambdaClient)

    resolver = SCGraphResolver(lambda_client=mock_lambda_client, maybe_sc_graph=mock_sc_graph)
    result = resolver.resolve(mock_vertex_dto)

    assert isinstance(result, SCGraphVertexResult)
    assert result.vertex == mock_vertex
    assert result.sc_graph == mock_sc_graph
    assert result.sc_graph.graph == mock_graph 
