"""Entrypoint for the Celium SDK.

Will expose Client and __version__
"""

from .client import Client
from .async_client import AsyncClient
from .version import VERSION as __version__

__all__ = ["Client", "AsyncClient", "__version__"]
