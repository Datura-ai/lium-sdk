"""AuthStrategy interface + helper Transport protocol."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Protocol


class Transport(Protocol):
    def request(self, method: str, path: str, **kw): ...
    async def arequest(self, method: str, path: str, **kw): ...
    def close(self) -> None: ...
    async def aclose(self) -> None: ...


class AuthStrategy(ABC):
    @abstractmethod
    def decorate(self, transport: Transport) -> Transport:
        """Return a proxy that injects credentials."""
        ...
