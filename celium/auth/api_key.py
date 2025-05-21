"""API key header injector."""
from __future__ import annotations

from .base import AuthStrategy, Transport


class ApiKeyAuth(AuthStrategy):
    _HEADER = "X-API-Key"

    def __init__(self, api_key: str | None):
        if not api_key:
            raise ValueError("api_key must be non-empty")
        self._api_key = api_key

    # ------------------ strategy entry ----------------- #
    def decorate(self, transport: Transport) -> Transport:
        api_key = self._api_key  # close over

        class _Proxy:  # runtime proxy; conforms to Transport
            def __init__(self, inner: Transport):
                self._inner = inner

            # sync
            def request(self, method: str, path: str, **kw):
                hdrs: dict[str, str] = kw.pop("headers", {}) or {}
                hdrs.setdefault(ApiKeyAuth._HEADER, api_key)
                return self._inner.request(method, path, headers=hdrs, **kw)

            # async
            async def arequest(self, method: str, path: str, **kw):
                hdrs: dict[str, str] = kw.pop("headers", {}) or {}
                hdrs.setdefault(ApiKeyAuth._HEADER, api_key)
                return await self._inner.arequest(method, path, headers=hdrs, **kw)

            # life-cycle passthrough
            def close(self) -> None: self._inner.close()
            async def aclose(self) -> None: await self._inner.aclose()

            def __getattr__(self, name: str):
                return getattr(self._inner, name)

        return _Proxy(transport)
