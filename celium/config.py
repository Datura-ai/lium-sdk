"""Centralised SDK defaults & env overrides."""
from __future__ import annotations

import os
import platform
from dataclasses import dataclass

__all__ = ["Config"]


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass(frozen=True, slots=True)
class Config:
    base_url: str = _env("CELIUM_BASE_URL", "https://celiumcompute.ai/api")
    timeout: float = float(_env("CELIUM_TIMEOUT", "10"))
    max_retries: int = int(_env("CELIUM_MAX_RETRIES", "2"))
    sdk_version: str = "0.1.0"
