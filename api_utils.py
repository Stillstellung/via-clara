"""
API response handling and validation utilities.
Provides standardized error handling and response formatting.
"""

from flask import jsonify
from typing import Tuple, Any, Optional, Union, Dict, List
import requests
from constants import HTTP_RATE_LIMIT, HTTP_SERVER_ERROR, HTTP_BAD_REQUEST


def handle_lifx_response(
    response: Union[requests.Response, Tuple],
    success_message: Optional[str] = None
) -> Tuple[Any, int]:
    """
    Standardized LIFX API response handler.

    Args:
        response: Either a requests.Response or error tuple
        success_message: Optional success message to include

    Returns:
        Tuple of (json_response, status_code)
    """
    # If response is already an error tuple, return it
    if isinstance(response, tuple):
        return response

    # Handle rate limiting
    if response.status_code == HTTP_RATE_LIMIT:
        return jsonify({
            "error": "LIFX API rate limit exceeded",
            "status_code": HTTP_RATE_LIMIT
        }), HTTP_RATE_LIMIT

    # Handle successful responses
    if 200 <= response.status_code < 300:
        try:
            data = response.json()
            if success_message:
                data['message'] = success_message
            return jsonify(data), response.status_code
        except Exception:
            return jsonify({
                "status": "success",
                "status_code": response.status_code
            }), response.status_code

    # Handle errors
    try:
        error_data = response.json()
    except Exception:
        error_data = {"error": "Unknown error"}

    return jsonify(error_data), response.status_code


def success_response(data: Dict[str, Any], status_code: int = 200) -> Tuple[Any, int]:
    """
    Create standardized success response.

    Args:
        data: Response data dictionary
        status_code: HTTP status code (default: 200)

    Returns:
        Tuple of (json_response, status_code)
    """
    return jsonify({"success": True, **data}), status_code


def error_response(
    message: str,
    status_code: int = HTTP_SERVER_ERROR,
    **extra_fields
) -> Tuple[Any, int]:
    """
    Create standardized error response.

    Args:
        message: Error message
        status_code: HTTP status code (default: 500)
        extra_fields: Additional fields to include in response

    Returns:
        Tuple of (json_response, status_code)
    """
    return jsonify({
        "success": False,
        "error": message,
        **extra_fields
    }), status_code


def validate_request_data(
    data: Any,
    required_fields: Optional[List[str]] = None
) -> Optional[Tuple[Any, int]]:
    """
    Validate request data has required fields.

    Args:
        data: Request data to validate
        required_fields: List of required field names (optional)

    Returns:
        Error response tuple if validation fails, None if valid
    """
    if not data:
        return error_response("No data provided", HTTP_BAD_REQUEST)

    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return error_response(
                f"Missing required fields: {', '.join(missing_fields)}",
                HTTP_BAD_REQUEST
            )

    return None
