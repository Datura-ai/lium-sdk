"""Async transport adapter using httpx.AsyncClient."""
from __future__ import annotations
from typing import Any

import httpx
from .base import ResponseLike, Transport
from ..utils.logging import logger, scrub_headers


class HttpxAsyncTransport(Transport):
    def __init__(
        self,
        *,
        base_url: str,
        default_headers: dict[str, str],
        timeout: float,
        max_retries: int,
    ):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)
        self._default_headers = default_headers
        self._max_retries = max_retries

    # -------------------------------------------------- #
    async def _do(
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

            resp = await self._client.request(
                method, url, params=params, json=json, headers=hdrs
            )

            if resp.status_code >= 500 and attempt < self._max_retries:
                continue
            return resp

    # ---------------------- async --------------------- #
    async def arequest(
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
        return await self._do(method, path, params=params, json=json, headers=headers)

    # --------------------- cleanup -------------------- #
    async def aclose(self) -> None:
        await self._client.aclose()
