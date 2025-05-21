"""Sync Client façade."""
from __future__ import annotations

from .config import Config
from .transport.httpx_sync import HttpxSyncTransport
from .auth.api_key import ApiKeyAuth
# Add resources here
from .transport.base import Transport


class Client:
    """Single public entry-point (sync)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        transport: Transport | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        self._config = Config()
        if base_url:
            object.__setattr__(self._config, "base_url", base_url)
        if timeout:
            object.__setattr__(self._config, "timeout", timeout)
        if max_retries is not None:
            object.__setattr__(self._config, "max_retries", max_retries)

        # -------------- core plumbing -------------- #
        self._transport = transport or HttpxSyncTransport(
            base_url=self._config.base_url,
            default_headers={"User-Agent": self._config.user_agent},
            timeout=self._config.timeout,
            max_retries=self._config.max_retries,
        )
        self._auth = ApiKeyAuth(api_key or "")

        # -------------- resources -------------- #
        secured = self._transport_with_auth

    # ============================================== #
    # Helpers
    # ============================================== #
    @property
    def _transport_with_auth(self) -> Transport:
        return self._auth.decorate(self._transport)

    # -------------- context mgr -------------- #
    def __enter__(self):  # sync
        return self

    def __exit__(self, *exc):
        self._transport.close()
