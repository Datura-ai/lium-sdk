"""Canonical error hierarchy + mapping helper."""
from __future__ import annotations
from typing import Any

__all__ = [
    "SDKError",
    "HTTPStatusError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
    "map_http_error",
]


class SDKError(Exception):
    """Root of all SDK-raised exceptions."""


class HTTPStatusError(SDKError):
    def __init__(self, status: int, body: Any, request_id: str | None = None):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body
        self.request_id = request_id


class AuthenticationError(HTTPStatusError): ...
class RateLimitError(HTTPStatusError): ...
class ValidationError(HTTPStatusError): ...
class ServerError(HTTPStatusError): ...


def map_http_error(status: int, body: Any, request_id: str | None = None) -> None:
    """Raise an appropriate typed error from raw HTTP metadata."""
    if status == 401:
        raise AuthenticationError(status, body, request_id)
    if status == 429:
        raise RateLimitError(status, body, request_id)
    if status in (400, 422):
        raise ValidationError(status, body, request_id)
    if 500 <= status < 600:
        raise ServerError(status, body, request_id)

    # Other non-2xx statuses:
    raise HTTPStatusError(status, body, request_id)
