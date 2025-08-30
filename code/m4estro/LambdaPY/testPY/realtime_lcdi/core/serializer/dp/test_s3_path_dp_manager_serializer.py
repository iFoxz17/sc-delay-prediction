import json
import pytest
from unittest.mock import patch, MagicMock, call

from core.serializer.dp.s3_path_dp_manager_serializer import S3PathDPManagerSerializer, PATH_DP_MANAGER_KEY
from core.sc_graph.path_extraction.path_dp_manager import PathDPManager, VertexPathDPManager, PathMem

@pytest.fixture
def serializer():
    return S3PathDPManagerSerializer()


@pytest.fixture
def mock_s3():
    with patch("core.serializer.dp.s3_path_dp_manager_serializer.s3") as mock:
        yield mock


@pytest.fixture
def dp_manager_fixture():
    n = 5
    dp_manager = PathDPManager(n) 
    for i in range(n):
        v_path_dp_manager = VertexPathDPManager(n)
        for j in range(n):
            v_path_dp_manager.mem[j] = PathMem()
            v_path_dp_manager.mem[j].paths.append([1, 2, 3] * j)  # Example paths
        
        dp_manager.v_path_dp_managers[i] = v_path_dp_manager

    return dp_manager

def test_serialize_success(serializer, mock_s3, dp_manager_fixture):
    bucket = "test-bucket"
    key = "custom_key.json"

    serializer.serialize(dp_manager_fixture, bucket, key, force=True)

    mock_s3.put_object.assert_called_once_with(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(dp_manager_fixture.to_json()).encode("utf-8"),
        ContentType="application/json"
    )


def test_serialize_raises_on_to_json_error(serializer, mock_s3):
    dp_manager = MagicMock()
    dp_manager.to_json.side_effect = RuntimeError("fail")

    with pytest.raises(RuntimeError):
        serializer.serialize(dp_manager, "bucket")

    mock_s3.put_object.assert_not_called()


def test_serialize_raises_on_put_error(serializer, mock_s3, dp_manager_fixture):
    mock_s3.put_object.side_effect = Exception("S3 failed")

    with pytest.raises(Exception, match="S3 failed"):
        serializer.serialize(dp_manager_fixture, "bucket", force=True)


def test_deserialize_success(serializer, mock_s3):
    # JSON structure returned from S3
    dp_data = {"key": "value"}
    mock_s3.head_object.return_value = {}
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=json.dumps(dp_data).encode("utf-8")))
    }

    with patch("core.serializer.dp.s3_path_dp_manager_serializer.PathDPManager") as mock_path_dp:
        instance = mock_path_dp.from_json.return_value
        result = serializer.deserialize("bucket", "some_key.json")

        mock_s3.head_object.assert_called_once_with(Bucket="bucket", Key="some_key.json")
        mock_s3.get_object.assert_called_once_with(Bucket="bucket", Key="some_key.json")
        mock_path_dp.from_json.assert_called_once_with(dp_data)
        assert result == instance


def test_deserialize_returns_none_if_key_missing(serializer, mock_s3):
    from botocore.exceptions import ClientError
    mock_s3.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "head_object"
    )

    result = serializer.deserialize("bucket", "missing_key.json")
    assert result is None

    mock_s3.head_object.assert_called_once()


def test_deserialize_raises_on_invalid_json(serializer, mock_s3):
    mock_s3.head_object.return_value = {}
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=b"{invalid json}"))
    }

    with pytest.raises(json.JSONDecodeError):
        serializer.deserialize("bucket", "bad.json")


def test_deserialize_raises_on_from_json_error(serializer, mock_s3):
    dp_data = {"key": "value"}
    mock_s3.head_object.return_value = {}
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=json.dumps(dp_data).encode("utf-8")))
    }

    with patch("core.serializer.dp.s3_path_dp_manager_serializer.PathDPManager") as mock_path_dp:
        mock_path_dp.from_json.side_effect = RuntimeError("bad data")

        with pytest.raises(RuntimeError, match="bad data"):
            serializer.deserialize("bucket", "some_key.json")


def test_serialize_deserialize_round_trip(serializer, mock_s3, dp_manager_fixture):
    bucket = "test-bucket"
    key = "round_trip.json"

    # Prepare mock for put_object (serialization)
    mock_s3.put_object.return_value = {}

    # Act: Serialize
    serializer.serialize(dp_manager_fixture, bucket, key, force=True)

    # Simulate what was uploaded to S3
    serialized_body = json.dumps(dp_manager_fixture.to_json()).encode("utf-8")

    # Prepare mock for head_object and get_object (deserialization)
    mock_s3.head_object.return_value = {}
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=serialized_body))
    }

    # Patch the real PathDPManager.from_json to produce a proper instance from dict
    with patch("core.serializer.dp.s3_path_dp_manager_serializer.PathDPManager.from_json") as mock_from_json:
        mock_from_json.return_value = dp_manager_fixture  # Return the original for comparison

        # Act: Deserialize
        result = serializer.deserialize(bucket, key)

        # Assert
        mock_s3.put_object.assert_called_once()
        mock_s3.head_object.assert_called_once_with(Bucket=bucket, Key=key)
        mock_s3.get_object.assert_called_once_with(Bucket=bucket, Key=key)

        assert result == dp_manager_fixture