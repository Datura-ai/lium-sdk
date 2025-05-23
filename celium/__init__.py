"""Entrypoint for the Celium SDK.

Will expose Client and __version__
"""

from .client import Client
from .async_client import AsyncClient
from .version import VERSION as __version__
from .models.executor import ExecutorFilterQuery, Executor
from .models.template import Template, TemplateCreate, TemplateUpdate


__all__ = [
    "Client", "AsyncClient", "__version__", "ExecutorFilterQuery", "Executor", "Template", 
    "TemplateCreate", "TemplateUpdate"
]
