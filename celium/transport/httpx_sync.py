"""Sync transport adapter powered by httpx.Client."""
from __future__ import annotations
from typing import Any

import httpx

from .base import ResponseLike, Transport
from ..utils.logging import logger, scrub_headers


class HttpxSyncTransport(Transport):
    def __init__(
        self,
        *,
        base_url: str,
        default_headers: dict[str, str],
        timeout: float,
        max_retries: int,
    ):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)
        self._default_headers = default_headers
        self._max_retries = max_retries

    # -------------------------------------------------- #
    def _do(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> ResponseLike:
        url = f"{self._base_url}{path}"
        hdrs = {**self._default_headers, **(headers or {})}

        for attempt in range(self._max_retries + 1):
            if attempt:
                logger.debug("Retrying {} {} (attempt {})", method, url, attempt + 1)

            resp = self._client.request(
                method, url, params=params, json=json, headers=hdrs
            )

            if resp.status_code >= 500 and attempt < self._max_retries:
                continue
            return resp  # may be non-2xx; resource will map to error.

    # ----------------------- sync ---------------------- #
    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
        **kwargs,
    ) -> ResponseLike:
        logger.debug(
            "HTTP  ➜  {} {}  hdrs={}",
            method,
            path,
            scrub_headers({**self._default_headers, **(headers or {})}),
        )
        return self._do(method, path, params=params, json=json, headers=headers)
    
    async def arequest(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ResponseLike: 
        raise NotImplementedError("Async requests are not supported yet")

    # --------------------- cleanup --------------------- #
    def close(self) -> None:
        self._client.close()
