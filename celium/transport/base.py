"""Transport protocol (sync + async) used by resources & auth layers."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Protocol


class ResponseLike(Protocol):
    status_code: int
    headers: dict[str, str]

    def json(self) -> Any: ...
    def text(self) -> str: ...


class Transport(ABC):
    """Abstract transport understood by resources."""

    # ----------------------- sync ----------------------- #
    @abstractmethod
    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ResponseLike: ...

    # ---------------------- async ----------------------- #
    @abstractmethod
    async def arequest(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ResponseLike: ...

    # ------------------- lifecycle ---------------------- #
    def close(self) -> None: ...
    async def aclose(self) -> None: ...
