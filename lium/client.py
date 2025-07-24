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
    """
    A client for the Lium API.

    Example usage::

        with lium.Client(api_key=API_KEY) as client:
            client.pods.list_executors()

    :ivar pods: Access to pod-related API methods.
    :vartype pods: Pods
    :ivar docker_credentials: Access to Docker credentials API methods.
    :vartype docker_credentials: DockerCredentials
    :ivar templates: Access to template-related API methods.
    :vartype templates: Templates
    :ivar ssh_keys: Access to SSH key management API methods.
    :vartype ssh_keys: SSHKeys
    """

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
        """
        Initialize the Lium API client.

        :param api_key: API key for authentication.
        :type api_key: str or None
        :param base_url: Base URL for the API endpoints.
        :type base_url: str or None
        :param transport: Custom transport instance to use for requests.
        :type transport: Transport or None
        :param timeout: Timeout for API requests in seconds.
        :type timeout: float or None
        :param max_retries: Maximum number of retries for failed requests.
        :type max_retries: int or None
        """
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
        """
        Return a transport instance decorated with authentication.

        :return: Authenticated transport instance.
        :rtype: Transport
        """
        return self._auth.decorate(self._transport)

    # -------------- context mgr -------------- #
    def __enter__(self):  # sync
        """
        Enter the runtime context related to this object.

        :return: The client instance itself.
        :rtype: Client
        """
        return self

    def __exit__(self, *exc):
        """
        Exit the runtime context and close the transport.

        :param exc: Exception information (if any).
        :type exc: tuple
        """
        self._transport.close()
