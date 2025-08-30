import os
import pytest
import igraph as ig
from tempfile import NamedTemporaryFile

from serializer.file_graph_serializer import FileGraphSerializer

# ------------------ TESTS ------------------

@pytest.fixture
def sample_graph():
    g = ig.Graph(directed=True)
    g.add_vertices(3)
    g.add_edges([(0, 1), (1, 2)])
    g.vs["name"] = ["NAME1", "NAME2", "NAME3"]
    g.vs["label"] = ["A", "B", "C"]
    g.es["weight"] = [1.0, 2.5]
    return g

def test_serialize_and_deserialize_graph(sample_graph):
    with NamedTemporaryFile(delete=False) as tmp:
        file_path = tmp.name

    try:
        serializer = FileGraphSerializer()
        serializer.serialize(sample_graph, file_path)

        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) > 0

        new_serializer = FileGraphSerializer()
        new_graph = new_serializer.deserialize(file_path)

        assert new_graph.vcount() == sample_graph.vcount()
        assert new_graph.ecount() == sample_graph.ecount()
        assert new_graph.vs["name"] == sample_graph.vs["name"]
        assert new_graph.vs["label"] == sample_graph.vs["label"]
        assert new_graph.es["weight"] == sample_graph.es["weight"]

    finally:
        os.remove(file_path)

def test_serialize_empty_graph():
    empty_graph = ig.Graph(directed=True)

    with NamedTemporaryFile(delete=False) as tmp:
        file_path = tmp.name

    try:
        serializer = FileGraphSerializer()
        serializer.serialize(empty_graph, file_path)

        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) > 0

        new_serializer = FileGraphSerializer()
        new_graph = new_serializer.deserialize(file_path)

        assert new_graph.vcount() == 0
        assert new_graph.ecount() == 0

    finally:
        os.remove(file_path)
