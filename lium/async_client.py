"""Async Client façade."""
from __future__ import annotations

from lium.resources.ssh_keys.async_ssh_keys import AsyncSSHKeys

from .config import Config
from .transport.httpx_async import HttpxAsyncTransport
from .auth.api_key import ApiKeyAuth
from .transport.base import Transport
from .resources.pods import AsyncPods
from .resources.docker_credentials import AsyncDockerCredentials
from .resources.templates.async_templates import AsyncTemplates


class AsyncClient:
    """
    Async variant (uses httpx.AsyncClient under the hood).

    Example usage::

        async with lium.AsyncClient(api_key=API_KEY) as client:
            await client.pods.list_executors()

    :ivar pods: Access to pod-related API methods (async).
    :vartype pods: AsyncPods
    :ivar docker_credentials: Access to Docker credentials API methods (async).
    :vartype docker_credentials: AsyncDockerCredentials
    :ivar templates: Access to template-related API methods (async).
    :vartype templates: AsyncTemplates
    :ivar ssh_keys: Access to SSH key management API methods (async).
    :vartype ssh_keys: AsyncSSHKeys
    """
    pods: AsyncPods
    docker_credentials: AsyncDockerCredentials
    templates: AsyncTemplates
    ssh_keys: AsyncSSHKeys

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        transport: Transport | None = None,
    ):
        """
        Initialize the Lium async API client.

        :param api_key: API key for authentication.
        :type api_key: str or None
        :param base_url: Base URL for the API endpoints.
        :type base_url: str or None
        :param timeout: Timeout for API requests in seconds.
        :type timeout: float or None
        :param max_retries: Maximum number of retries for failed requests.
        :type max_retries: int or None
        :param transport: Custom transport instance to use for requests.
        :type transport: Transport or None
        """
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
        self.pods = AsyncPods(secured, self)
        self.docker_credentials = AsyncDockerCredentials(secured, self)
        self.templates = AsyncTemplates(secured, self)
        self.ssh_keys = AsyncSSHKeys(secured, self)
        
    # ------------------------------------------------- #
    @property
    def _transport_with_auth(self) -> Transport:
        """
        Return a transport instance decorated with authentication.

        :return: Authenticated transport instance.
        :rtype: Transport
        """
        return self._auth.decorate(self._transport)

    # ---------------- context mgr ------------------- #
    async def __aenter__(self):  # async context
        """
        Enter the async runtime context related to this object.

        :return: The async client instance itself.
        :rtype: AsyncClient
        """
        return self

    async def __aexit__(self, *exc):
        """
        Exit the async runtime context and close the transport.

        :param exc: Exception information (if any).
        :type exc: tuple
        """
        await self._transport.aclose()
