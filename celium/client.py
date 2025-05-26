"""Sync Client façade."""
from __future__ import annotations

from .config import Config
from .transport.httpx_sync import HttpxSyncTransport
from .auth.api_key import ApiKeyAuth
# Add resources here
from .resources.pods import Pods
from .resources.docker_credentials import DockerCredentials
from .transport.base import Transport
from .resources.templates import Templates
from .resources.ssh_keys import SSHKeys


class Client:
    """Single public entry-point (sync)."""

    # -------------- resources -------------- #
    pods: Pods
    docker_credentials: DockerCredentials
    templates: Templates
    ssh_keys: SSHKeys

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
            default_headers={},
            timeout=self._config.timeout,
            max_retries=self._config.max_retries,
        )
        self._auth = ApiKeyAuth(api_key or "")

        # -------------- resources -------------- #
        secured = self._transport_with_auth
        self.pods = Pods(secured, self)
        self.docker_credentials = DockerCredentials(secured, self)
        self.templates = Templates(secured, self)
        self.ssh_keys = SSHKeys(secured, self)
        
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
