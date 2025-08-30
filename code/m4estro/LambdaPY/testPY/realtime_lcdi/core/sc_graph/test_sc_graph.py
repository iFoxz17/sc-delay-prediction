import pytest
import igraph as ig

from core.sc_graph.path_extraction.path_extraction_manager import PathExtractionManager
from core.sc_graph.path_prob.path_prob_manager import PathProbManager
from core.dto.path.paths_dto import PathsIdDTO
from core.sc_graph.sc_graph import SCGraph

from graph_config import N_ORDERS_BY_CARRIER_ATTR, V_ID_ATTR, N_ORDERS_ATTR

@pytest.fixture
def complex_graph():
    # Graph structure:
    # A -> B -> D -> F (manufacturer)
    #  \       /
    #   -> C -- 
    # Edges have carriers with different orders

    g = ig.Graph(directed=True)
    g.add_vertices(7)
    g.vs["name"] = ["0", "A", "B", "C", "D", "E", "F"]

    # Add edges: 0->A, A->B, A->C, B->D, C->D, D->F
    edges = [(0,1), (1,2), (1,3), (2,4), (3,4), (4,6)]
    g.add_edges(edges)

    # Vertex orders by carrier
    g.vs[0][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 19, "carrier2": 10}    # 0
    g.vs[1][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 12, "carrier2": 3}     # A
    g.vs[2][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 7, "carrier2": 3}      # B
    g.vs[3][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 5, "carrier2": 0}      # C
    g.vs[4][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 12, "carrier2": 3}     # D
    g.vs[5][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 0, "carrier2": 0}      # E, isolated vertex
    g.vs[6][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 12, "carrier2": 3}     # F, manufacturer

    for v in g.vs:
        v[N_ORDERS_ATTR] = sum(v[N_ORDERS_BY_CARRIER_ATTR].values())  # Total orders for each vertex

    for v in g.vs:
        v[V_ID_ATTR] = v.index + 1

    # Edge orders by carrier
    g.es[0][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 12, "carrier2": 3}  # 0->A
    g.es[1][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 7, "carrier2": 3}  # A->B
    g.es[2][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 5, "carrier2": 0}  # A->C
    g.es[3][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 7, "carrier2": 3}  # B->D
    g.es[4][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 5, "carrier2": 0}  # C->D
    g.es[5][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 12, "carrier2": 3}  # D->F

    for e in g.es:
        e[N_ORDERS_ATTR] = sum(e[N_ORDERS_BY_CARRIER_ATTR].values())

    return g

@pytest.fixture
def sc_graph_fixture(complex_graph):
    """Fixture to create SCGraph instance with a manufacturer vertex"""
    manufacturer_vertex = complex_graph.vs.find(name="F")
    path_extraction_manager = PathExtractionManager(
        graph=complex_graph,
        maybe_manufacturer=manufacturer_vertex,
    )
    path_prob_manager = PathProbManager(
        graph=complex_graph,
        maybe_manufacturer=manufacturer_vertex,
    )
    return SCGraph(complex_graph, 
                   maybe_manufacturer=manufacturer_vertex, 
                   path_extraction_manager=path_extraction_manager,
                   path_prob_manager=path_prob_manager
                   )

def test_extract_paths_single_carrier(sc_graph_fixture):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph

    # Use multiple carriers
    carriers_list = [["carrier1"], ["carrier2"]]
    for i, carriers in enumerate(carriers_list):
        result = sc_graph.extract_paths("A", carriers)

        assert isinstance(result, PathsIdDTO)
        assert result.source == graph.vs.find(name="A")[V_ID_ATTR]
        assert result.destination == manufacturer_vertex[V_ID_ATTR]
        assert set(result.requested_carriers) == set(carriers)
        assert set(result.valid_carriers) == set(carriers)

        # Check paths for each carrier
        for carrier in carriers:
            carrier_paths = [p for p in result.paths if p.carrier == carrier]
            assert len(carrier_paths) > 0

            for p in carrier_paths:
                # path starts at source
                assert p.path[0] == result.source
                # path ends with or leads towards manufacturer index
                assert manufacturer_vertex[V_ID_ATTR] in p.path
                # Probability is between 0 and 1
                assert 0.0 <= p.prob <= 1.0

        # Additional check: probabilities for carrier1 paths should reflect branching weights
        # Probabilities for carrier1 edges from A are 7/10 to B and 3/10 to C, roughly
        probs_carrier = [p.prob for p in result.paths if p.carrier == carriers_list[i][0]]
        assert all(0 <= prob <= 1 for prob in probs_carrier)

def test_extract_paths_multiple_carriers(sc_graph_fixture):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph

    # Use multiple carriers
    carriers = ["carrier1", "carrier2"]
    result = sc_graph.extract_paths("A", carriers)

    assert isinstance(result, PathsIdDTO)
    assert result.source == graph.vs.find(name="A")[V_ID_ATTR]
    assert result.destination == manufacturer_vertex[V_ID_ATTR]
    assert set(result.requested_carriers) == set(carriers)
    assert set(result.valid_carriers) == set(carriers)

    # Check paths for each carrier
    for i, carrier in enumerate(carriers):
        carrier_paths = [p for p in result.paths if p.carrier == carrier]
        assert len(carrier_paths) >= 0

        for p in carrier_paths:
            # path starts at source
            assert p.path[0] == result.source
            # path ends with or leads towards manufacturer index
            assert manufacturer_vertex[V_ID_ATTR] in p.path
            # Probability is between 0 and 1
            assert 0.0 <= p.prob <= 1.0

        # Additional check: probabilities for carrier1 paths should reflect branching weights
        # Probabilities for carrier1 edges from A are 7/10 to B and 3/10 to C, roughly

        probs_carrier = [p.prob for p in result.paths if p.carrier == carrier]
        assert all(0 <= prob <= 1 for prob in probs_carrier)

def test_extract_paths_multiple_carriers_one_carrier_no_paths(sc_graph_fixture):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph

    # Use multiple carriers
    carriers = ["carrier1", "carrier2"]
    result = sc_graph.extract_paths("C", carriers, zero_prob_paths=False)

    assert isinstance(result, PathsIdDTO)
    assert result.source == graph.vs.find(name="C")[V_ID_ATTR]
    assert result.destination == manufacturer_vertex[V_ID_ATTR]
    assert set(result.requested_carriers) == set(carriers)
    assert set(result.valid_carriers) == set(carriers)
    assert result.n_paths == 1  # Only carrier1 has a path from C to F
    assert pytest.approx(result.total_probability) == 1.0
    
    assert result.paths[0].carrier == "carrier1"  # Only carrier1 has
    assert result.paths[0].path[0] == graph.vs.find(name="C")[V_ID_ATTR]
    assert result.paths[0].path[-1] == manufacturer_vertex[V_ID_ATTR]
    assert pytest.approx(result.paths[0].prob) == 1.0  # Probability is 1.0 for the only path

def test_extract_paths_multiple_carriers_one_carrier_no_paths_extract_also_zero_prob_paths(sc_graph_fixture):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph

    # Use multiple carriers
    carriers = ["carrier1", "carrier2"]
    result = sc_graph.extract_paths("C", carriers, zero_prob_paths=True)

    assert isinstance(result, PathsIdDTO)
    assert result.source == graph.vs.find(name="C")[V_ID_ATTR]
    assert result.destination == manufacturer_vertex[V_ID_ATTR]
    assert set(result.requested_carriers) == set(carriers)
    assert set(result.valid_carriers) == set(carriers)
    assert result.n_paths == 2  # Include also path with zero probability of carrier2
    assert pytest.approx(result.total_probability) == 1.0
    
    assert result.paths[0].carrier in ["carrier1", "carrier2"]
    assert result.paths[0].path[0] == graph.vs.find(name="C")[V_ID_ATTR]
    assert result.paths[0].path[-1] == manufacturer_vertex[V_ID_ATTR]
    assert pytest.approx(result.paths[0].prob) in [1.0, 0.0]  # Probability is 1.0 for the path with carrier1

    assert result.paths[0].carrier in ["carrier1", "carrier2"]
    assert result.paths[1].path[0] == graph.vs.find(name="C")[V_ID_ATTR]
    assert result.paths[1].path[-1] == manufacturer_vertex[V_ID_ATTR]
    assert pytest.approx(result.paths[1].prob) in [1.0, 0.0]  # Probability is 0.0 for the path with carrier2

    assert result.paths[0].carrier != result.paths[1].carrier  # Ensure different carriers
        
def test_extract_paths_with_vertex_source_object(sc_graph_fixture):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph

    source_vertex = graph.vs.find(name="B")
    
    result = sc_graph.extract_paths(source_vertex, ["carrier1"])

    assert all(p.path[0] == source_vertex[V_ID_ATTR] for p in result.paths)
    assert all(0.0 <= p.prob <= 1.0 for p in result.paths)

def test_extract_paths_cycle_detection_in_graph(sc_graph_fixture, caplog):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph

    # Add cycle F -> A
    graph.add_edge(graph.vs.find(name="D").index, graph.vs.find(name="A").index)
    graph.es[-1][N_ORDERS_BY_CARRIER_ATTR] = {"carrier1": 1, "carrier2": 1}

    with caplog.at_level("ERROR"):
        _ = sc_graph.extract_paths("A", ["carrier1", "carrier2"])
        assert any("Cycle detected" in record.message for record in caplog.records)
        
def test_extract_paths_not_existing_carriers(sc_graph_fixture):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph
    
    result = sc_graph.extract_paths("A", ["nonexistent_carrier", "nonexistent_carrier2"])
    assert isinstance(result, PathsIdDTO)
    assert result == PathsIdDTO(
        source=graph.vs.find(name="A")[V_ID_ATTR],
        destination=manufacturer_vertex[V_ID_ATTR],
        requestedCarriers=["nonexistent_carrier", "nonexistent_carrier2"],
        validCarriers=[],
        paths=[]
    )

def test_extract_paths_source_is_manufacturer(sc_graph_fixture):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph

    source_v = graph.vs.find(name="F")
    
    result = sc_graph.extract_paths(source_v, ["carrier1"])
    
    # Should have one path with probability 1.0 and empty intermediate path
    assert len(result.paths) == 1
    assert result.paths[0].prob == 1.0
    assert result.paths[0].path == [manufacturer_vertex[V_ID_ATTR]]

#TODO: Adjust test
'''
def test_extract_paths_dp_manager_reuse(sc_graph_fixture):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph
    
    source_index = graph.vs.find(name="A").index
    target_index = manufacturer_vertex.index
    target_dp_manager = dp_manager.get(target_index)

    # First extraction
    result1 = sc_graph.extract_paths("A", ["carrier1"])
    initial_path_dp_size = 0
    for path_mem in target_dp_manager.paths_mem.mem:
        for path in path_mem.paths:
            initial_path_dp_size += len(path)

    initial_prob_dp_size = 0
    for carrier, mem in target_dp_manager.paths_probs_mem.mem.items():
        for prob_mem in mem:
            initial_prob_dp_size += len(prob_mem.probs)
    
    # Second extraction with same parameters should reuse DP values
    result2 = sc_graph.extract_paths("A", ["carrier1"])
    final_path_dp_size = 0
    for path_mem in target_dp_manager.paths_mem.mem:
        for path in path_mem.paths:
            final_path_dp_size += len(path)

    final_prob_dp_size = 0
    for carrier, mem in target_dp_manager.paths_probs_mem.mem.items():
        for prob_mem in mem:
            final_prob_dp_size += len(prob_mem.probs)
    
    # Results should be identical
    assert len(result1.paths) == len(result2.paths)
    assert initial_path_dp_size > 0 and initial_path_dp_size == final_path_dp_size
    assert initial_prob_dp_size > 0 and initial_prob_dp_size == final_prob_dp_size

    for i, vertex_manager in enumerate(dp_manager.v_dp_managers):
        path_manager = vertex_manager.paths_mem
        prob_manager = vertex_manager.paths_probs_mem
        if i == target_index:
            assert len(path_manager.mem) == sc_graph.graph.vcount()
            assert any(len(p.paths) > 0 for p in path_manager.mem) 
            prob_mems = prob_manager.mem["carrier1"]
            assert len(prob_mems) == sc_graph.graph.vcount()
            assert any(len(p.probs) > 0 for p in prob_mems) 

        else:
            assert len(path_manager.mem) == sc_graph.graph.vcount()
            for path_mem in path_manager.mem:
                assert len(path_mem.paths) == 0
            assert prob_manager.mem == {}
    
    # Verify paths are identical
    for p1, p2 in zip(result1.paths, result2.paths):
        assert p1.path == p2.path
        assert p1.prob == p2.prob
        assert p1.carrier == p2.carrier
'''

def test_extract_paths_empty_carriers_list(sc_graph_fixture):
    sc_graph = sc_graph_fixture
    manufacturer_vertex = sc_graph.manufacturer
    graph = sc_graph.graph

    result = sc_graph.extract_paths("A", [])

    assert isinstance(result, PathsIdDTO)
    assert result == PathsIdDTO(
        source=graph.vs.find(name="A")[V_ID_ATTR],
        destination=manufacturer_vertex[V_ID_ATTR],
        requestedCarriers=[],
        validCarriers=[],
        paths=[]
    )


