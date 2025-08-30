import pytest
from unittest.mock import MagicMock
import igraph as ig

from core.serializer.s3_sc_graph_serializer import S3SCGraphSerializer
from core.sc_graph.sc_graph import SCGraph
from core.sc_graph.path_extraction.path_extraction_manager import PathExtractionManager
from core.sc_graph.path_prob.path_prob_manager import PathProbManager
from core.sc_graph.path_extraction.path_dp_manager import PathDPManager
from core.sc_graph.path_prob.path_prob_dp_manager import PathProbDPManager

from model.vertex import VertexType
from graph_config import TYPE_ATTR


@pytest.fixture
def mock_serializers():
    return {
        "graph_serializer": MagicMock(),
        "path_dp_serializer": MagicMock(),
        "path_prob_dp_serializer": MagicMock()
    }


@pytest.fixture
def serializer(mock_serializers):
    return S3SCGraphSerializer(
        graph_serializer=mock_serializers["graph_serializer"],
        path_dp_manager_serializer=mock_serializers["path_dp_serializer"],
        path_prob_dp_manager_serializer=mock_serializers["path_prob_dp_serializer"]
    )


@pytest.fixture
def manufacturer_graph():
    graph = ig.Graph()
    graph.add_vertex(name="Manufacturer", type=VertexType.MANUFACTURER.value)
    graph.add_vertex(name="I1", type=VertexType.INTERMEDIATE.value)
    graph.add_vertex(name="I2", type=VertexType.INTERMEDIATE.value)
    graph.add_vertex(name="I3", type=VertexType.INTERMEDIATE.value)
    graph.add_vertex(name="S1", type=VertexType.SUPPLIER_SITE.value)
    graph.add_vertex(name="S2", type=VertexType.SUPPLIER_SITE.value)
    
    return graph


@pytest.fixture
def sc_graph(manufacturer_graph):
    manufacturer = manufacturer_graph.vs[0]
    path_dp_manager = PathDPManager(manufacturer_graph.vcount())
    path_prob_dp_manager = PathProbDPManager(manufacturer_graph.vcount())
    pem = PathExtractionManager(manufacturer_graph, manufacturer, path_dp_manager)
    ppm = PathProbManager(manufacturer_graph, manufacturer, path_prob_dp_manager)
    return SCGraph(
        graph=manufacturer_graph,
        maybe_manufacturer=manufacturer,
        path_extraction_manager=pem,
        path_prob_manager=ppm
    )


def test_serialize_calls_all(mock_serializers, serializer, sc_graph):
    bucket = "test-bucket"
    force = False
    serializer.serialize(sc_graph, bucket, force)

    mock_serializers["graph_serializer"].serialize.assert_called_once_with(sc_graph.graph, bucket)
    mock_serializers["path_dp_serializer"].serialize.assert_called_once_with(
        sc_graph.path_extraction_manager.dp_manager, bucket, force=force
    )
    mock_serializers["path_prob_dp_serializer"].serialize.assert_called_once_with(
        sc_graph.path_prob_manager.dp_manager, bucket, force=force
    )


def test_deserialize_returns_sc_graph(mock_serializers, serializer, manufacturer_graph):
    bucket = "test-bucket"
    manufacturer = manufacturer_graph.vs.find(type=VertexType.MANUFACTURER.value)

    mock_serializers["graph_serializer"].deserialize.return_value = manufacturer_graph
    mock_serializers["path_dp_serializer"].deserialize.return_value = PathDPManager(manufacturer_graph.vcount())
    mock_serializers["path_prob_dp_serializer"].deserialize.return_value = PathProbDPManager(manufacturer_graph.vcount())

    result = serializer.deserialize(bucket)

    assert isinstance(result, SCGraph)
    assert result.graph == manufacturer_graph
    assert result.manufacturer == manufacturer
    assert isinstance(result.path_extraction_manager, PathExtractionManager)
    assert isinstance(result.path_prob_manager, PathProbManager)


def test_deserialize_raises_without_manufacturer(mock_serializers, serializer):
    graph = ig.Graph()
    graph.add_vertex(name="NoM", type="warehouse")  # No MANUFACTURER

    mock_serializers["graph_serializer"].deserialize.return_value = graph

    with pytest.raises(ValueError, match="Manufacturer vertex not found"):
        serializer.deserialize("test-bucket")
