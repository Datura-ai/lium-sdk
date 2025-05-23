"""Async Client façade."""
from __future__ import annotations

from .config import Config
from .transport.httpx_async import HttpxAsyncTransport
from .auth.api_key import ApiKeyAuth
from .transport.base import Transport
from .resources.pods import AsyncPods
from .resources.docker_credentials import AsyncDockerCredentials
from .resources.templates.async_templates import AsyncTemplates


class AsyncClient:
    """Async variant (uses httpx.AsyncClient under the hood)."""
    pods: AsyncPods
    docker_credentials: AsyncDockerCredentials
    templates: AsyncTemplates

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        transport: Transport | None = None,
    ):
        self._config = Config()
        if base_url:
            object.__setattr__(self._config, "base_url", base_url)
        if timeout:
            object.__setattr__(self._config, "timeout", timeout)
        if max_retries is not None:
            object.__setattr__(self._config, "max_retries", max_retries)

        self._transport = transport or HttpxAsyncTransport(
            base_url=self._config.base_url,
            default_headers={},
            timeout=self._config.timeout,
            max_retries=self._config.max_retries,
        )
        self._auth = ApiKeyAuth(api_key or "")

        # -------------- resources -------------- #
        secured = self._transport_with_auth
        self.pods = AsyncPods(secured)
        self.docker_credentials = AsyncDockerCredentials(secured)
        self.templates = AsyncTemplates(secured)

    # ------------------------------------------------- #
    @property
    def _transport_with_auth(self) -> Transport:
        return self._auth.decorate(self._transport)

    # ---------------- context mgr ------------------- #
    async def __aenter__(self):  # async context
        return self

    async def __aexit__(self, *exc):
        await self._transport.aclose()
