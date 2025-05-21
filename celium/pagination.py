"""Transparent cursor-based iteration."""
from __future__ import annotations
from typing import Any, Callable, Iterator, TypeVar

T = TypeVar("T")


class CursorIterator(Iterator[T]):
    def __init__(self, resource, filters: dict[str, Any]):
        self._resource = resource
        self._cursor: str | None = None
        self._buf: list[T] = []
        self._filters = filters

    def __next__(self) -> T:
        if not self._buf:
            params = {**self._filters, "cursor": self._cursor}
            resp = self._resource._t.request("GET", self._resource.ENDPOINT, params=params)
            payload = self._resource._get_json(resp)
            self._buf = payload["items"]
            self._cursor = payload.get("next_cursor")
            if not self._buf:
                raise StopIteration
        return self._buf.pop(0)
