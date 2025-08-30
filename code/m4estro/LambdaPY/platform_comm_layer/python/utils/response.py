from typing import List, Dict, Optional
import json
from aws_lambda_powertools.event_handler.api_gateway import Response

from utils.config import COMMON_API_HEADERS

INDENT = 2

def success_response(data: Dict | List) -> Response:
    return Response(
        status_code=200,
        body=json.dumps(data, indent=INDENT),
        headers=COMMON_API_HEADERS
    )

def created_response(location_url: str, data: Optional[Dict | List] = None) -> Response:
    return Response(
        status_code=201,
        body=json.dumps(data, indent=INDENT) if data else "",
        headers={
            **COMMON_API_HEADERS,
            "Location": location_url
        }
    )

def multi_status_response(location_url: str, data: List, add_location_header: bool = False) -> Response:
    headers: Dict[str, str] = COMMON_API_HEADERS.copy()
    if add_location_header:
        headers["Location"] = location_url
    return Response(
        status_code=207,
        body=json.dumps(data, indent=INDENT),
        headers=headers
    )

def bad_request_response(error_message: str) -> Response:
    return Response(
        status_code=400,
        body=json.dumps({"message": error_message}, indent=INDENT),
        headers=COMMON_API_HEADERS
    )

def not_found_response(error_message: str) -> Response:
    return Response(
        status_code=404,
        body=json.dumps({"message": error_message}, indent=INDENT),
        headers=COMMON_API_HEADERS
    )

def internal_error_response(error_message: str, data: Optional[Dict | List] = None) -> Response:
    body: Dict = {"message": error_message}
    if data is not None:
        body["data"] = data

    return Response(
        status_code=500,
        body=json.dumps(body, indent=INDENT),
        headers=COMMON_API_HEADERS
    )

def unprocessable_entity_response(message: str, data: Optional[Dict | List] = None) -> Response:
    body: Dict = {"message": message}
    if data is not None:
        body["data"] = data
    return Response(
        status_code=422,
        body=json.dumps(body, indent=INDENT),
        headers=COMMON_API_HEADERS
    )