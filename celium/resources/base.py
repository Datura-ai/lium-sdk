"""Common helper inherited by all resource wrappers."""
from __future__ import annotations
from typing import Any

from ..transport.base import Transport
from ..exceptions import map_http_error


class BaseResource:
    def __init__(self, transport: Transport):
        self._t = transport

    # ----------------------------------------------- #
    def _get_json(self, resp) -> Any:
        if resp.status_code // 100 != 2:
            rid = resp.headers.get("x-request-id")
            map_http_error(resp.status_code, resp.text, rid)
        return resp.json()
