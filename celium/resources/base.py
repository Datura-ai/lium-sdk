"""Common helper inherited by all resource wrappers."""
from __future__ import annotations
from typing import Any, TYPE_CHECKING

from ..transport.base import Transport
from ..exceptions import map_http_error
if TYPE_CHECKING:
    from celium import Client, AsyncClient


class _BaseResource:
    _t: Transport
    
    # ----------------------------------------------- #
    def _get_json(self, resp) -> Any:
        if resp.status_code // 100 != 2:
            rid = resp.headers.get("x-request-id")
            map_http_error(resp.status_code, resp.text, rid)
        return resp.json()
    

class BaseResource(_BaseResource):
    _client: "Client"
    
    def __init__(self, transport: Transport, client: "Client"):
        self._t = transport
        self._client = client


class BaseAsyncResource(_BaseResource):
    _client: "AsyncClient"
    
    def __init__(self, transport: Transport, client: "AsyncClient"):
        self._t = transport
        self._client = client

    # ----------------------------------------------- #
    async def _get_json(self, resp) -> Any:
        if resp.status_code // 100 != 2:
            rid = resp.headers.get("x-request-id")
            map_http_error(resp.status_code, resp.text, rid)
        return await resp.json()