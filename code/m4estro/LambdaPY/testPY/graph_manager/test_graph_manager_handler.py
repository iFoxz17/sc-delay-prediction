import pytest
import json
from unittest.mock import patch

from graph_manager_handler import (
    handle_graph_build,
    handle_graph_retrieval,
)
from graph_manager_dto.q_params import GraphManagerQParamsKeys
from utils.response import INDENT

QUERY_PARAMS = {}

@pytest.fixture
def fake_app(monkeypatch):
    class FakeEvent:
        def __init__(self):
            self.query_string_parameters = QUERY_PARAMS
            self.json_body = json.dumps({})

    class FakeApp:
        def __init__(self):
            self.current_event = FakeEvent()

    monkeypatch.setattr("graph_manager_handler.app", FakeApp())
    return FakeApp()


def test_handle_graph_build_created(fake_app):
    with patch("graph_manager_handler.build_graph", return_value=None) as mock_build:
        response = handle_graph_build()
        assert response.status_code == 201
        assert "Location" in response.headers
        assert response.headers["Location"] == "/lcdi/sc-graph"
        mock_build.assert_called_once()


def test_handle_graph_retrieval_success_default(fake_app):
    with patch("graph_manager_handler.get_graph_data", return_value={"nodes": [], "edges": []}) as mock_get:
        response = handle_graph_retrieval()
        assert response.status_code == 200
        assert response.body == json.dumps({"nodes": [], "edges": []}, indent=INDENT)
        mock_get.assert_called_once()

def test_handle_graph_retrieval_intermediate_true(fake_app):
    QUERY_PARAMS[GraphManagerQParamsKeys.INTERMEDIATE.value] = "true"
    
    with patch("graph_manager_handler.get_graph_data", return_value={"nodes": ["X"], "edges": ["Y"]}) as mock_get:
        response = handle_graph_retrieval()
        assert response.status_code == 200
        assert response.body == json.dumps({"nodes": ["X"], "edges": ["Y"]}, indent=INDENT)
        mock_get.assert_called_once()
    
    QUERY_PARAMS.clear()  # Clear for next test

def test_handle_graph_retrieval_intermediate_false(fake_app):
    QUERY_PARAMS[GraphManagerQParamsKeys.INTERMEDIATE.value] = "false"
    
    with patch("graph_manager_handler.get_map_data", return_value={"nodes": ["X"], "edges": ["Y"]}) as mock_get:
        response = handle_graph_retrieval()
        assert response.status_code == 200
        assert response.body == json.dumps({"nodes": ["X"], "edges": ["Y"]}, indent=INDENT)
        mock_get.assert_called_once()
    
    QUERY_PARAMS.clear()  # Clear for next test

def test_handle_graph_retrieval_intermediate_any(fake_app):
    QUERY_PARAMS[GraphManagerQParamsKeys.INTERMEDIATE.value] = "any_value"
    
    with patch("graph_manager_handler.get_graph_data", return_value={"nodes": ["X"], "edges": ["Y"]}) as mock_get:
        response = handle_graph_retrieval()
        assert response.status_code == 200
        assert response.body == json.dumps({"nodes": ["X"], "edges": ["Y"]}, indent=INDENT)
        mock_get.assert_called_once()
    
    QUERY_PARAMS.clear()  # Clear for next test

