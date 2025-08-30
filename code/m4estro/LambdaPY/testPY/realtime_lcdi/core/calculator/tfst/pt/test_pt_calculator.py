import pytest
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import igraph as ig

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO

from core.query_handler.params.params_result import PTParams

from core.dto.path.prob_path_dto import ProbPathIdDTO
from core.dto.path.paths_dto import PathsIdDTO

from core.calculator.tfst.pt.pt_input_dto import PTInputDTO
from core.calculator.tfst.pt.pt_dto import PT_DTO

from core.calculator.tfst.pt.tmi.tmi_manager import TMIValueDTO
from core.calculator.tfst.pt.wmi.wmi_manager import WMIValueDTO

from core.calculator.tfst.pt.pt_calculator import PTCalculator
from core.sc_graph.sc_graph import SCGraph
from core.calculator.tfst.pt.vertex_time.vertex_time_dto import VertexTimeDTO
from core.calculator.tfst.pt.route_time.route_time_dto import RouteTimeDTO

from model.vertex import VertexType

# Graph constants
from graph_config import (
    V_ID_ATTR,
    TYPE_ATTR,
    LATITUDE_ATTR,
    LONGITUDE_ATTR,
    AVG_ORI_ATTR,
    DISTANCE_ATTR,
    AVG_OTI_ATTR,
    AVG_WMI_ATTR,
    AVG_TMI_ATTR
)

@pytest.fixture
def extended_graph():
    g = ig.Graph(directed=True)
    
    # Add 4 vertices now
    g.add_vertices(4)

    g.vs[0][V_ID_ATTR] = 1
    g.vs[0]['name'] = "Supplier Site"
    g.vs[0][TYPE_ATTR] = VertexType.SUPPLIER_SITE.value
    g.vs[0][AVG_ORI_ATTR] = 10.0
    g.vs[0][LATITUDE_ATTR] = 10.0
    g.vs[0][LONGITUDE_ATTR] = 20.0

    g.vs[1][V_ID_ATTR] = 2
    g.vs[1]['name'] = "Intermediate 1"
    g.vs[1][TYPE_ATTR] = VertexType.INTERMEDIATE.value
    g.vs[1][AVG_ORI_ATTR] = 5.0
    g.vs[1][LATITUDE_ATTR] = 15.0
    g.vs[1][LONGITUDE_ATTR] = 25.0

    g.vs[2][V_ID_ATTR] = 3
    g.vs[2]['name'] = "Intermediate 2"
    g.vs[2][TYPE_ATTR] = VertexType.INTERMEDIATE.value
    g.vs[2][AVG_ORI_ATTR] = 4.0
    g.vs[2][LATITUDE_ATTR] = 17.0
    g.vs[2][LONGITUDE_ATTR] = 27.0

    g.vs[3][V_ID_ATTR] = 4
    g.vs[3]['name'] = "Manufacturer"
    g.vs[3][TYPE_ATTR] = VertexType.MANUFACTURER.value
    g.vs[3][AVG_ORI_ATTR] = 2.0
    g.vs[3][LATITUDE_ATTR] = 20.0
    g.vs[3][LONGITUDE_ATTR] = 30.0

    # Add edges 1→2, 2→3, 3→4
    g.add_edges([(0, 1), (1, 2), (2, 3)])
    for i, e in enumerate(g.es):
        e[DISTANCE_ATTR] = 100.0 + i
        e[AVG_OTI_ATTR] = 10.0
        e[AVG_WMI_ATTR] = 1.0
        e[AVG_TMI_ATTR] = 1.0

    return g

@pytest.fixture
def mocked_calculators():
    vt_calculator = MagicMock()
    # 4 vertices now
    vt_calculator.calculate.side_effect = [
        VertexTimeDTO(lower=5.0, upper=6.0),    # vertex 2
        VertexTimeDTO(lower=4.0, upper=5.0),    # vertex 3
    ]

    rt_calculator = MagicMock()
    # 3 edges now
    rt_calculator.calculate.side_effect = [
        RouteTimeDTO(lower=4.0, upper=6.0),  # edge 1→2
        RouteTimeDTO(lower=2.0, upper=3.0),  # edge 2→3
        RouteTimeDTO(lower=1.0, upper=2.0)   # edge 3→4
    ]

    tmi_manager = MagicMock()
    tmi_manager.calculate_tmi.side_effect = [
        TMIValueDTO(value=0.2, computed=True),  # TMI for edge 1→2
        TMIValueDTO(value=0.3, computed=True),  # TMI for edge 2→3
        TMIValueDTO(value=0.4, computed=True)   # TMI for edge 3→4
    ]

    wmi_manager = MagicMock()
    wmi_manager.calculate_wmi.side_effect = [
        WMIValueDTO(value=0.5, computed=True),  # WMI for edge 1→2
        WMIValueDTO(value=0.6, computed=True),  # WMI for edge 2→3
        WMIValueDTO(value=0.7, computed=True)   # WMI for edge 3→4
    ]

    return vt_calculator, rt_calculator, tmi_manager, wmi_manager

@pytest.fixture
def pt_calculator(extended_graph, mocked_calculators):
    sc_graph = MagicMock(spec=SCGraph)
    sc_graph.graph = extended_graph
    vt_calculator, rt_calculator, tmi_manager, wmi_manager = mocked_calculators

    return PTCalculator(sc_graph=sc_graph,
                        vt_calculator=vt_calculator,
                        rt_calculator=rt_calculator,
                        tmi_manager=tmi_manager,
                        wmi_manager=wmi_manager,
                        params=PTParams(
                            rte_estimator_params=MagicMock(from_autospec=True),
                            tmi_params= MagicMock(from_autospec=True),
                            wmi_params=MagicMock(from_autospec=True),
                            path_min_probability=0.0,
                            max_paths=10,
                            ext_data_min_probability=0.0,
                            confidence=0.95
                        ))

def test_path_no_time_adjustment(pt_calculator):
    path = [1, 2, 3, 4]
    epsilon = 0.01

    event_time = datetime.now(timezone.utc)
    lower, upper, tmi, wmi = pt_calculator._calculate_path_time(path, 0.9, event_time, datetime.now(timezone.utc))

    # Calculation breakdown:
    # Vertex 1 (supplier): 0 h (skipped)
    # Route 1→2: 4–6h -> average 5h
    # Vertex 2: 5–6h -> average 5.5h
    # Route 2→3: 2–3h -> average 2.5h
    # Vertex 3: 4–5h -> average 4.5h
    # Route 3→4: 1–2h -> average 1.5h
    # Vertex 4 (manufacturer): 0 h (skipped)
    expected_lower = 0 + 4 + 5 + 2 + 4 + 1 + 0 - epsilon  # 16h, epsilon accounts for the current_time - event_time adjustment
    expected_upper = 0 + 6 + 6 + 3 + 5 + 2 + 0  # 22h

    assert expected_lower <= lower <= expected_upper
    assert expected_lower <= upper <= expected_upper
    assert lower <= upper
    assert pytest.approx(tmi) == 0.2
    assert pytest.approx(wmi) == 0.5

def test_path_with_time_adjustment(pt_calculator):
    pt_calculator.rt_calculator.calculate(0, 0)         # Pop the first call to avoid first route
    pt_calculator.tmi_manager.calculate_tmi()            # Pop the first call to avoid first route
    pt_calculator.wmi_manager.calculate_wmi()            # Pop the first call to avoid first route

    path = [2, 3, 4]
    epsilon = 0.01
    delta = 2.0
        
    event_time = datetime.now(timezone.utc) - timedelta(hours=delta)  # 2 hours ago
    lower, upper, tmi, wmi = pt_calculator._calculate_path_time(path, 0.9, event_time, datetime.now(timezone.utc))

    # Calculation breakdown:
    # Vertex 2: 5–6h -> average 5.5h
    # Route 2→3: 2–3h -> average 2.5h
    # Vertex 3: 4–5h -> average 4.5h
    # Route 3→4: 1–2h -> average 1.5h
    # Vertex 4 (manufacturer): 0 h (skipped)
    expected_lower = (5 - delta) + 2 + 4 + 1 + 0 - epsilon  # 10h, epsilon accounts for the current_time - event_time adjustment
    expected_upper = (6 - delta) + 3 + 5 + 2 + 0  # 14h

    assert expected_lower <= lower <= expected_upper
    assert expected_lower <= upper <= expected_upper
    assert lower <= upper

    assert pytest.approx(tmi) == 0.3
    assert pytest.approx(wmi) == 0.6

def test_path_with_time_adjustment_exceding(pt_calculator):
    pt_calculator.rt_calculator.calculate(0, 0)         # Pop the first call to avoid first route
    pt_calculator.tmi_manager.calculate_tmi()            # Pop the first call to avoid first route
    pt_calculator.wmi_manager.calculate_wmi()            # Pop the first call to avoid first route

    path = [2, 3, 4]
    epsilon = 0.01
    delta = 10.0
        
    event_time = datetime.now(timezone.utc) - timedelta(hours=delta)  # 10 hours ago
    lower, upper, tmi, wmi = pt_calculator._calculate_path_time(path, 0.9, event_time, datetime.now(timezone.utc))

    # Calculation breakdown:
    # Vertex 2: 5–6h -> average 5.5h
    # Route 2→3: 2–3h -> average 2.5h
    # Vertex 3: 4–5h -> average 4.5h
    # Route 3→4: 1–2h -> average 1.5h
    # Vertex 4 (manufacturer): 0 h (skipped)
    expected_lower = (0) + 2 + 4 + 1 + 0 - epsilon  # 7h, epsilon accounts for the current_time - event_time adjustment
    expected_upper = (0) + 3 + 5 + 2 + 0  # 10h

    assert expected_lower <= lower <= expected_upper
    assert expected_lower <= upper <= expected_upper
    assert lower <= upper

    assert pytest.approx(tmi) == 0.3
    assert pytest.approx(wmi) == 0.6

def test_path_with_single_vertex(pt_calculator):
    delta = 1.0
    event_time = datetime.now(timezone.utc) - timedelta(hours=delta)
    path = [2]

    # Vertex 2: 5–6h -> average 5.5h

    lower, upper, wmi, tmi = pt_calculator._calculate_path_time(path, 0.9, event_time, datetime.now(timezone.utc))

    # Vertex 1 adjusted by 1h elapsed: 9–11h
    assert 5 - delta - 0.01 <= lower <= 6 - delta
    assert 5 - delta <= upper <= 6 - delta
    assert lower <= upper

    assert pytest.approx(tmi) == 0.0
    assert pytest.approx(wmi) == 0.0


def test_calculate_remaining_time(pt_calculator):
    probs = [0.5, 0.3, 0.2]  # Probabilities for each path
    lowers = [5.0, 10.0, 7.0]  # Lower times for each path
    uppers = [7.0, 11.0, 8.0]  # Upper times for each path
    tmi_values = [0.5, 0.6, 0.4]  # TMI for each path
    wmi_values = [0.3, 0.4, 0.2]  # WMI for each path
    
    # Setup paths with probabilities and dummy paths
    path1 = ProbPathIdDTO(path=[1, 2, 5], prob=probs[0], carrier="CarrierA")
    path2 = ProbPathIdDTO(path=[1, 2, 3, 4, 5], prob=probs[1], carrier="CarrierA")
    path3 = ProbPathIdDTO(path=[1, 2, 3, 5], prob=probs[2], carrier="CarrierA")
    paths_dto = PathsIdDTO(paths=[path1, path2, path3], source=1, destination=5, requestedCarriers=["CarrierA"], validCarriers=["CarrierA"])
    
    # Mock the sc_graph.extract_paths to return these paths
    pt_calculator.sc_graph.extract_paths = MagicMock(return_value=paths_dto)
    
    # Patch _calculate_path_time to return fixed values per path to avoid deep complexity
    def mock_calc_path_time(path, prob, starting_time, current_time):
        if path == [1, 2, 5]:
            return (lowers[0], uppers[0], tmi_values[0], wmi_values[0])
        elif path == [1, 2, 3, 4, 5]:
            return (lowers[1], uppers[1], tmi_values[1], wmi_values[1])
        elif path == [1, 2, 3, 5]:
            return (lowers[2], uppers[2], tmi_values[2], wmi_values[2])
        else:
            return (0.0, 0.0, 0.0, 0.0)
    
    pt_calculator._calculate_path_time = MagicMock(side_effect=mock_calc_path_time)

    estimation_time = datetime.now(timezone.utc)                     # t   
    event_time = estimation_time - timedelta(hours=1)                # timestamp of the last event
    starting_time = estimation_time - timedelta(hours=40)            # t1
     
    pt_dto = pt_calculator.calculate_remaining_time(
        PTInputDTO(vertex_id=2, carrier_names=["CarrierA"]), 
        event_time=event_time, 
        estimation_time=estimation_time
    )

    expected_lower = np.dot(probs, lowers)
    expected_upper = np.dot(probs, uppers)
    
    assert pytest.approx(pt_dto.lower) == expected_lower
    assert pytest.approx(pt_dto.upper) == expected_upper
    assert pt_dto.params.confidence == pt_calculator.params.confidence
    assert pt_dto.n_paths == len(paths_dto.paths)

    expected_avg_tmi = np.dot(probs, tmi_values)
    expected_avg_wmi = np.dot(probs, wmi_values)

    actual_avg_tmi = pt_dto.avg_tmi
    actual_avg_wmi = pt_dto.avg_wmi

    assert pytest.approx(actual_avg_tmi) == expected_avg_tmi
    assert pytest.approx(actual_avg_wmi) == expected_avg_wmi

def test_calculate_remaining_time_no_paths(pt_calculator):
    # Setup a vertex ID and mock vertex
    g = ig.Graph(directed=True)
    vertex_id = 1
    v = g.add_vertex(name="Vertex1", type=VertexType.SUPPLIER_SITE.value)
    v[V_ID_ATTR] = vertex_id

    pt_calculator.sc_graph.graph = g

    path_1 = ProbPathIdDTO(path=[], prob=1.0, carrier="CarrierA")  # Empty path
    pt_calculator.sc_graph.extract_paths = MagicMock(
        return_value=PathsIdDTO(paths=[path_1], source=1, destination=5, requestedCarriers=["CarrierA"], validCarriers=["CarrierA"])
    )

    # Provide valid datetime inputs
    estimation_time = datetime.now(timezone.utc)  # e.g. t
    event_time = estimation_time - timedelta(hours=1)
    starting_time = estimation_time - timedelta(hours=10)  # e.g. t1

    # Run the method
    pt_dto = pt_calculator.calculate_remaining_time(
        PTInputDTO(vertex_id=vertex_id, carrier_names=["CarrierA"]), 
        event_time=event_time, 
        estimation_time=estimation_time
    )

    # Assert expected outputs for empty path
    assert pt_dto.lower == 0.0
    assert pt_dto.upper == 0.0
    assert pt_dto.params.confidence == pt_calculator.params.confidence
    assert pt_dto.n_paths == 0
    assert pt_dto.avg_tmi == 0.0
    assert pt_dto.avg_wmi == 0.0

def test_calculate_remaining_time_exception_in_path_time_single_failure(pt_calculator):
    g = ig.Graph(directed=True)
    vertex_id = 1
    v = g.add_vertex(name="Vertex1", type=VertexType.SUPPLIER_SITE.value)
    v[V_ID_ATTR] = vertex_id

    pt_calculator.sc_graph.graph = g

    # Setup paths with one path that will raise in _calculate_path_time
    path1 = ProbPathIdDTO(path=[1, 2, 3], prob=0.5, carrier="CarrierA")
    path2 = ProbPathIdDTO(path=[4, 5, 6], prob=0.5, carrier="CarrierB")
    paths_dto = PathsIdDTO(paths=[path1, path2], source=1, destination=6, requestedCarriers=["CarrierA", "CarrierB"], validCarriers=["CarrierA", "CarrierB"])

    pt_calculator.sc_graph.extract_paths = MagicMock(return_value=paths_dto)

    # Patch _calculate_path_time so path1 raises, path2 returns normal
    def mock_calc_path_time(path, prob, starting_time, current_time):
        if path == [1, 2, 3]:
            raise RuntimeError("Calculation error")
        elif path == [4, 5, 6]:
            return (8.0, 10.0, 0.4, 0.3)  # Normal path time with TMI and WMI
        else:
            return (0.0, 0.0)

    pt_calculator._calculate_path_time = MagicMock(side_effect=mock_calc_path_time)

    estimation_time = datetime.now(timezone.utc)  # e.g. t
    event_time = estimation_time - timedelta(hours=1)
    starting_time = estimation_time - timedelta(hours=10)  # e.g. t1

    pt_dto = pt_calculator.calculate_remaining_time(
        PTInputDTO(vertex_id=vertex_id, carrier_names=["CarrierA", "CarrierB"]), 
                   event_time=event_time, 
                   estimation_time=estimation_time
    )

    # Only path2 counted, so lower and upper should be from path2
    assert pytest.approx(pt_dto.lower) == 8.0
    assert pytest.approx(pt_dto.upper) == 10.0
    assert pt_dto.params.confidence == pt_calculator.params.confidence
    assert pt_dto.n_paths == 1  # Only path2 counted
    assert pytest.approx(pt_dto.avg_tmi) == 0.4
    assert pytest.approx(pt_dto.avg_wmi) == 0.3

def test_calculate_remaining_time_exception_in_path_time_double_failure(pt_calculator):
    # Setup a vertex
    g = ig.Graph(directed=True)
    vertex_id = 1
    v = g.add_vertex(name="Vertex1", type=VertexType.SUPPLIER_SITE.value)
    v[V_ID_ATTR] = vertex_id

    pt_calculator.sc_graph.graph = g

    # Setup 4 paths, path2 will raise exception
    path1 = ProbPathIdDTO(path=[1, 2, 3], prob=0.3, carrier="CarrierA")
    path2 = ProbPathIdDTO(path=[4, 5, 6], prob=0.2, carrier="CarrierB")  # will raise
    path3 = ProbPathIdDTO(path=[7, 8, 9], prob=0.25, carrier="CarrierA") # will raise
    path4 = ProbPathIdDTO(path=[10, 11, 12], prob=0.25, carrier="CarrierB")
    paths_dto = PathsIdDTO(paths=[path1, path2, path3, path4], source=1, destination=12, requestedCarriers=["CarrierA", "CarrierB"], validCarriers=["CarrierA", "CarrierB"])

    pt_calculator.sc_graph.extract_paths = MagicMock(return_value=paths_dto)

    # Patch _calculate_path_time so path2 raises, others return normal times
    def mock_calc_path_time(path, prob, starting_time, current_time):
        if path == [4, 5, 6]:
            raise RuntimeError("Calculation error")
        elif path == [1, 2, 3]:
            return (5.0, 6.0, 0.3, 0.2)  # Normal path time with TMI and WMI
        elif path == [7, 8, 9]:
            raise RuntimeError("Calculation error")
        elif path == [10, 11, 12]:
            return (9.0, 10.0, 0.25, 0.3)  # Normal path time with TMI and WMI
        else:
            return (0.0, 0.0)

    pt_calculator._calculate_path_time = MagicMock(side_effect=mock_calc_path_time)

    estimation_time = datetime.now(timezone.utc)  # e.g. t
    event_time = estimation_time - timedelta(hours=1)  # timestamp of the last event
    starting_time = estimation_time - timedelta(hours=10)
    
    pt_dto = pt_calculator.calculate_remaining_time(
        PTInputDTO(vertex_id=vertex_id, carrier_names=["CarrierA", "CarrierB"]), 
        event_time=event_time, 
        estimation_time=estimation_time
    )

    failed_prob = path2.prob + path3.prob  # 0.2 + 0.25 = 0.45
    expected_lower = (0.3 / (1 - failed_prob) * 5.0) + (0.25 / (1 - failed_prob) * 9.0)
    expected_upper = (0.3 / (1 - failed_prob) * 6.0) + (0.25 / (1 - failed_prob) * 10.0)

    assert pytest.approx(pt_dto.lower) == expected_lower
    assert pytest.approx(pt_dto.upper) == expected_upper
    assert pt_dto.params.confidence == pt_calculator.params.confidence
    assert pt_dto.n_paths == 2  # Only path1 and path4 counted

    expected_avg_tmi = (0.3 / (1 - failed_prob) * 0.3) + (0.25 / (1 - failed_prob) * 0.25)
    expected_avg_wmi = (0.3 / (1 - failed_prob) * 0.2) + (0.25 / (1 - failed_prob) * 0.3)

    actual_avg_tmi = pt_dto.avg_tmi
    actual_avg_wmi = pt_dto.avg_wmi

    assert pytest.approx(actual_avg_tmi) == expected_avg_tmi
    assert pytest.approx(actual_avg_wmi) == expected_avg_wmi


def test_calculate_total_processing_time_estimate(pt_calculator):
    g = ig.Graph(directed=True)
    vertex_id = 1
    v = g.add_vertex(name="Vertex1", type=VertexType.SUPPLIER_SITE.value)
    v[V_ID_ATTR] = vertex_id

    pt_calculator.sc_graph.graph = g

    estimation_time = datetime.now(timezone.utc)                     # t   
    event_time = estimation_time - timedelta(hours=1)                # timestamp of the last event
    shipment_time = estimation_time - timedelta(hours=40)            # e.g. t1
    order_time = shipment_time - timedelta(hours=12)                 # t0

    time_sequence = TimeSequenceDTO(
        order_time=order_time,
        shipment_time=shipment_time,
        event_time=event_time,
        estimation_time=estimation_time
    )
    
    # Total elapsed hours
    shipment_elapsed_hours = (estimation_time - shipment_time).total_seconds() / 3600.0

    # Mock calculate_remaining_time to return a fixed PT_DTO
    fixed_remaining = PT_DTO(lower=3.0, 
                             upper=4.0, 
                             avg_tmi=0.5, 
                             avg_wmi=0.6, 
                             n_paths=5,
                             params=PTParams(
                                 rte_estimator_params=MagicMock(from_autospec=True),
                                 tmi_params=MagicMock(from_autospec=True),
                                 wmi_params=MagicMock(from_autospec=True),
                                 path_min_probability=0.0,
                                 max_paths=10,
                                 ext_data_min_probability=0.0,
                                 confidence=0.95
                                 ))
                            
    pt_calculator.calculate_remaining_time = MagicMock(return_value=fixed_remaining)

    # Use datetime objects directly in the DTO
    pt_input = PTInputDTO(
        vertex_id=vertex_id,
        carrier_names=["CarrierA"],
    )

    pt = pt_calculator.calculate(pt_input, time_sequence=time_sequence)

    # total lower = elapsed + remaining lower
    # total upper = elapsed + remaining upper
    assert pytest.approx(pt.lower) == (fixed_remaining.lower)
    assert pytest.approx(pt.upper) == (fixed_remaining.upper)
    assert pt.params.confidence == pt_calculator.params.confidence
    assert pt.n_paths == fixed_remaining.n_paths

    assert pytest.approx(pt.avg_tmi) == fixed_remaining.avg_tmi
    assert pytest.approx(pt.avg_wmi) == fixed_remaining.avg_wmi