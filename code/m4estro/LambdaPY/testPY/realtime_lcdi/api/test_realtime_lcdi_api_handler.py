import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timezone

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.api_gateway import APIGatewayRestResolver

from graph_config import V_ID_ATTR
from api.route.realtime_lcdi_route import register_routes, REALTIME_LCDI_PATH
from api.dto.order_estimation.order_estimation_response import OrderEstimationStatus
from resolver.vertex_not_found_exception import VertexNotFoundException
from core.exception.invalid_time_sequence_exception import InvalidTimeSequenceException
from core.exception.prob_path_exception import ProbPathException


@pytest.fixture
def app():
    app = APIGatewayRestResolver()
    register_routes(app)
    return app


def make_event(path: str, method="GET", query_params=None, body=None):
    event = {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query_params or {}
    }
    if body is not None:
        event["body"] = json.dumps(body) if isinstance(body, (dict, list)) else body
    return event


class DummyVertexResult:
    def __init__(self, vertex, sc_graph):
        self.vertex = vertex
        self.sc_graph = sc_graph


FAKE_VERTEX_RESULT = DummyVertexResult({V_ID_ATTR: 1}, "dummy_sc_graph")


# --------------------------------------------------------------
# Tests GET /lcdi/realtime
# --------------------------------------------------------------

def test_handle_retrieve_realtime_lcdi_success(app):
    response_body = [
        {
            "order_id": 1023,
            "manufacturer_order_id": 89234,
            "tracking_number": "DHL1234567890",
            "carrier": "DHL Express",
            "site": {"id": 17, "location": "Berlin, DE"},
            "supplier": {"id": 42, "manufacturer_id": 1205, "name": "Continental Supplies GmbH"},
            "AODT": 2.3,
            "ODI": 0.85,
            "status": "DISPATCH",
            "data": [{}],
        }
    ]

    with patch("api.route.realtime_lcdi_route.get_realtime_lcdi_by_order", return_value=response_body):
        event = make_event(REALTIME_LCDI_PATH, query_params={"order": "1023"})
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 200
        body = response.get("body")
        assert body is not None
        assert "order_id" in body


def test_handle_retrieve_realtime_lcdi_internal_error(app):
    with patch("api.route.realtime_lcdi_route.get_realtime_lcdi_by_order", side_effect=Exception("boom")):
        event = make_event(REALTIME_LCDI_PATH, query_params={"order": "1023"})
        response = app.resolve(event, LambdaContext())
        assert response["statusCode"] == 500


# --------------------------------------------------------------
# Tests POST /lcdi/realtime
# --------------------------------------------------------------

def test_handle_compute_realtime_lcdi_single_created(app):
    single_request = {
        "vertex": {"vertex_id": 1}, 
        "order_id": 1023, 
        "event_time": "2023-10-01T12:00:00Z"
    }

    with patch("api.route.realtime_lcdi_route.compute_order_realtime_lcdi", return_value={"id": 123, "data": "some data"}) as mock_compute, \
         patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator

        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.return_value = FAKE_VERTEX_RESULT
        MockResolver.return_value = mock_resolver_instance

        event = make_event(REALTIME_LCDI_PATH, method="POST", body=single_request)
        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 201
        assert "Location" in response["multiValueHeaders"]
        assert response["multiValueHeaders"]["Location"][0].endswith("/123")

        body = json.loads(response["body"])
        assert "id" in body
        assert "data" in body

        mock_compute.assert_called_once()


def test_handle_compute_realtime_lcdi_list_single_created(app):
    single_request = [{
        "vertex": {"vertex_id": 1}, 
        "order_id": 1023, 
        "event_time": "2023-10-01T12:00:00Z"
    }]

    with patch("api.route.realtime_lcdi_route.compute_order_realtime_lcdi", return_value={"id": 123, "data": "some data"}) as mock_compute, \
         patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator
        
        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.return_value = FAKE_VERTEX_RESULT
        MockResolver.return_value = mock_resolver_instance

        event = make_event(REALTIME_LCDI_PATH, method="POST", body=single_request)
        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 201
        assert "Location" in response["multiValueHeaders"]
        
        body = json.loads(response["body"])
        assert len(body) == 1
        assert body[0]["id"] == 123
        assert body[0]["location"].endswith("/123")

        mock_compute.assert_called_once()


def test_handle_compute_realtime_lcdi_list_created(app):
    multiple_requests = [
        {"vertex": {"vertex_id": 1}, "order_id": 1023, "event_time": "2023-10-01T12:00:00Z"},
        {"vertex": {"vertexName": "test_name"}, "order_id": 1024, "event_time": "2023-10-01T12:05:00Z", "estimation_time": "2023-10-01T12:06:00Z"},
        {"vertex": {"vertexName": "test_name1", "vertexType": "INTERMEDIATE"}, "order_id": 1025, "event_time": "2023-10-01T12:10:00Z", "estimation_time": "2023-10-01T12:11:00Z"}
    ]

    with patch("api.route.realtime_lcdi_route.compute_order_realtime_lcdi", return_value={"id": 123, "data": "some data"}) as mock_compute, \
         patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator
        
        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.return_value = FAKE_VERTEX_RESULT
        MockResolver.return_value = mock_resolver_instance
        
        event = make_event(REALTIME_LCDI_PATH, method="POST", body=multiple_requests)
        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 201
        assert "Location" in response["multiValueHeaders"]
        
        body = json.loads(response["body"])
        assert len(body) == 3
        for item in body:
            assert item["id"] == 123
            assert item["location"].endswith("/123")

        assert mock_compute.call_count == 3


def test_handle_compute_realtime_lcdi_single_error(app):
    single_request = {
        "vertex": {"vertex_id": 1}, 
        "order_id": 1023, 
        "event_time": "2023-10-01T12:00:00Z"
    }
         
    with patch("api.route.realtime_lcdi_route.compute_order_realtime_lcdi", side_effect=Exception("boom")) as mock_compute, \
         patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator

        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.return_value = FAKE_VERTEX_RESULT
        MockResolver.return_value = mock_resolver_instance

        event = make_event(REALTIME_LCDI_PATH, method="POST", body=single_request)
        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 500
        assert "Location" not in response.get("headers", {})

        body = json.loads(response["body"])
        assert "message" in body

        mock_compute.assert_called_once()


def test_handle_compute_realtime_lcdi_multiple_partial_error(app):
    multiple_requests = [
        {"vertex": {"vertex_id": 1}, "order_id": 1023, "event_time": "2023-10-01T12:00:00Z"},
        {"vertex": {"vertexName": "test_name"}, "order_id": 1024, "event_time": "2023-10-01T12:05:00Z"},
        {"vertex": {"vertexName": "test_name1"}, "order_id": 1025, "event_time": "2023-10-01T12:10:00Z"}
    ]

    side_effects = [
        {"id": 100},
        Exception("failed"),
        Exception("failed")
    ]
    
    with patch("api.route.realtime_lcdi_route.compute_order_realtime_lcdi", side_effect=side_effects) as mock_compute, \
         patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator
        
        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.return_value = FAKE_VERTEX_RESULT
        MockResolver.return_value = mock_resolver_instance

        event = make_event(REALTIME_LCDI_PATH, method="POST", body=multiple_requests)
        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 207
        assert "Location" in response["multiValueHeaders"]
        
        body = json.loads(response["body"])
        assert len(body) == 3
        assert body[0]["status"] == OrderEstimationStatus.CREATED.value
        assert body[1]["status"] == OrderEstimationStatus.ERROR.value
        assert body[2]["status"] == OrderEstimationStatus.ERROR.value
        assert "location" in body[0]
        assert "id" in body[0]
        assert "message" in body[1]
        assert "message" in body[2]

        assert mock_compute.call_count == 3


def test_handle_compute_realtime_lcdi_multiple_only_errors(app):
    multiple_requests = [
        {"vertex": {"vertex_id": 1}, "order_id": 1023, "event_time": "2023-10-01T12:00:00Z"},
        {"vertex": {"vertexName": "test_name"}, "order_id": 1024, "event_time": "2023-10-01T12:05:00Z"},
        {"vertex": {"vertexName": "test_name1"}, "order_id": 1025, "event_time": "2023-10-01T12:10:00Z"}
    ]

    with patch("api.route.realtime_lcdi_route.compute_order_realtime_lcdi", side_effect=Exception("boom")) as mock_compute, \
         patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator
        
        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.return_value = FAKE_VERTEX_RESULT
        MockResolver.return_value = mock_resolver_instance

        event = make_event(REALTIME_LCDI_PATH, method="POST", body=multiple_requests)
        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 500
        assert "Location" not in response.get("headers", {})
        
        body = json.loads(response["body"])
        assert "message" in body

        assert mock_compute.call_count == 3


def test_handle_compute_realtime_lcdi_single_failed(app):
    single_request = {
        "vertex": {"vertex_id": 1}, 
        "order_id": 1023, 
        "event_time": "2023-10-01T12:00:00Z"
    }

    with patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator
        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.side_effect = VertexNotFoundException("Vertex not found")
        MockResolver.return_value = mock_resolver_instance
        
        event = make_event(REALTIME_LCDI_PATH, method="POST", body=single_request)
        response = app.resolve(event, LambdaContext())
        
        assert response["statusCode"] == 422
        assert "Location" not in response.get("headers", {})
        
        body = json.loads(response["body"])
        assert "message" in body
        assert "Vertex not found" in body["message"]


def test_handle_compute_realtime_lcdi_multiple_partial_failed(app):
    multiple_requests = [
        {"vertex": {"vertex_id": 1}, "order_id": 1023, "event_time": "2023-10-01T12:00:00Z"},
        {"vertex": {"vertexName": "test_name"}, "order_id": 1024, "event_time": "2023-10-01T12:05:00Z"},
        {"vertex": {"vertexName": "test_name1"}, "order_id": 1025, "event_time": "2023-10-01T12:10:00Z"}
    ]

    side_effects = [
        {"id": 100},
        InvalidTimeSequenceException("Invalid time sequence",
                                     datetime(2023, 10, 1, 12, 5, tzinfo=timezone.utc),
                                     datetime(2023, 10, 1, 12, 6, tzinfo=timezone.utc),
                                     datetime(2023, 10, 1, 12, 10, tzinfo=timezone.utc),
                                     datetime(2023, 10, 1, 12, 11, tzinfo=timezone.utc)),
        ProbPathException("Path extraction failed")
    ]

    with patch("api.route.realtime_lcdi_route.compute_order_realtime_lcdi", side_effect=side_effects) as mock_compute, \
         patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator
            
        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.return_value = FAKE_VERTEX_RESULT
        MockResolver.return_value = mock_resolver_instance

        event = make_event(REALTIME_LCDI_PATH, method="POST", body=multiple_requests)
        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 207
        assert "Location" in response["multiValueHeaders"]
        
        body = json.loads(response["body"])
        assert len(body) == 3
        assert body[0]["status"] == OrderEstimationStatus.CREATED.value
        assert body[1]["status"] == OrderEstimationStatus.FAILED.value
        assert body[2]["status"] == OrderEstimationStatus.FAILED.value
        assert "location" in body[0]
        assert "id" in body[0]
        assert "message" in body[1]
        assert "Invalid time sequence" in body[1]["message"]
        assert "message" in body[2]
        assert "Path extraction failed" in body[2]["message"]

        assert mock_compute.call_count == 3


def test_handle_compute_realtime_lcdi_multiple_only_failed(app):
    multiple_requests = [
        {"vertex": {"vertex_id": 1}, "order_id": 1023, "event_time": "2023-10-01T12:00:00Z"},
        {"vertex": {"vertexName": "test_name"}, "order_id": 1024, "event_time": "2023-10-01T12:05:00Z"},
        {"vertex": {"vertexName": "test_name1"}, "order_id": 1025, "event_time": "2023-10-01T12:10:00Z"}
    ]

    side_effects = [
        ProbPathException("Could not extract path for vertex 1"),
        InvalidTimeSequenceException("Invalid time sequence",
                                     datetime(2023, 10, 1, 12, 5, tzinfo=timezone.utc),
                                     datetime(2023, 10, 1, 12, 6, tzinfo=timezone.utc),
                                     datetime(2023, 10, 1, 12, 10, tzinfo=timezone.utc),
                                     datetime(2023, 10, 1, 12, 11, tzinfo=timezone.utc)),
        VertexNotFoundException("Vertex 3 not found")
    ]

    with patch("api.route.realtime_lcdi_route.compute_order_realtime_lcdi", side_effect=side_effects) as mock_compute, \
         patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator
            
        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.return_value = FAKE_VERTEX_RESULT
        MockResolver.return_value = mock_resolver_instance

        event = make_event(REALTIME_LCDI_PATH, method="POST", body=multiple_requests)
        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 422
        assert "Location" not in response.get("headers", {})
        
        body = json.loads(response["body"])
        assert "message" in body
        assert "data" in body
        
        body_list = body['data']
        assert len(body_list) == 3
        assert all(item["status"] == OrderEstimationStatus.FAILED.value for item in body_list)
        assert "message" in body_list[0]
        assert "message" in body_list[1]
        assert "message" in body_list[2]

        assert mock_compute.call_count == 3


def test_handle_compute_realtime_lcdi_multiple_mixed_errors_and_failures(app):
    multiple_requests = [
        {"vertex": {"vertex_id": 1}, "order_id": 1023, "event_time": "2023-10-01T12:00:00Z"},
        {"vertex": {"vertexName": "test_name"}, "order_id": 1024, "event_time": "2023-10-01T12:05:00Z"},
        {"vertex": {"vertexName": "test_name1"}, "order_id": 1025, "event_time": "2023-10-01T12:10:00Z"}
    ]

    side_effects = [
        VertexNotFoundException("Vertex 1 not found"),
        Exception("Database connection error"),
        InvalidTimeSequenceException("Invalid time sequence",
                                     datetime(2023, 10, 1, 12, 5, tzinfo=timezone.utc),
                                     datetime(2023, 10, 1, 12, 6, tzinfo=timezone.utc),
                                     datetime(2023, 10, 1, 12, 10, tzinfo=timezone.utc),
                                     datetime(2023, 10, 1, 12, 11, tzinfo=timezone.utc)),
    ]

    with patch("api.route.realtime_lcdi_route.compute_order_realtime_lcdi", side_effect=side_effects) as mock_compute, \
         patch("api.route.realtime_lcdi_route.SCGraphResolver") as MockResolver, \
         patch("api.route.realtime_lcdi_route.BucketDataLoader") as MockBucketLoader, \
         patch("boto3.client") as mock_boto3_client:

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3  # Prevent real S3 client creation

        mock_loader_instance = MockBucketLoader.return_value
        mock_rt_estimator = MagicMock()
        mock_loader_instance.load_route_time_estimator.return_value = mock_rt_estimator
        
        mock_resolver_instance = MagicMock()
        mock_resolver_instance.resolve.return_value = FAKE_VERTEX_RESULT
        MockResolver.return_value = mock_resolver_instance

        event = make_event(REALTIME_LCDI_PATH, method="POST", body=multiple_requests)
        response = app.resolve(event, LambdaContext())

        assert response["statusCode"] == 207
        assert "Location" not in response.get("headers", {})
        
        body = json.loads(response["body"])
        assert len(body) == 3

        assert body[0]["status"] == OrderEstimationStatus.FAILED.value
        assert body[1]["status"] == OrderEstimationStatus.ERROR.value
        assert body[2]["status"] == OrderEstimationStatus.FAILED.value

        assert mock_compute.call_count == 3


def test_handle_compute_realtime_lcdi_bad_request(app):
    invalid_request = {"invalid": "data"}

    event = make_event(REALTIME_LCDI_PATH, method="POST", body=invalid_request)
    response = app.resolve(event, LambdaContext())

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "message" in body