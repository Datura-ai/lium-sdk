"""SDK-wide logging helper powered by Loguru.

Usage
-----
from ..utils.logging import logger

logger.info("hello {}", "world")
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from loguru import logger as _logger  # ← actual Loguru instance

__all__ = ["logger"]

# --------------------------------------------------------------------------- #
# 1. Decide log level based on env var
# --------------------------------------------------------------------------- #
_DEBUG = os.getenv("CELIUM_SDK_DEBUG") == "1"
_LEVEL: Literal["DEBUG", "INFO"] = "DEBUG" if _DEBUG else "INFO"

# --------------------------------------------------------------------------- #
# 2. Remove default sink (Loguru auto-adds one) and install our own
#    so we can tweak format & rotation without affecting host apps.
# --------------------------------------------------------------------------- #
_logger.remove()

_fmt = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
)

# Console sink — stderr
_logger.add(
    sink=sys.stderr,
    level=_LEVEL,
    format=_fmt,
    enqueue=False,  # micro-perf: we’re mostly IO-bound anyway
    backtrace=False,
    diagnose=False,  # keep tracebacks clean for SDK users
)

# Optional file sink — only if CELIUM_SDK_LOG_PATH is set
if (log_path := os.getenv("CELIUM_SDK_LOG_PATH")):
    log_file = Path(log_path).expanduser()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    _logger.add(
        sink=str(log_file),
        rotation="10 MB",
        retention="14 days",
        level=_LEVEL,
        format=_fmt,
        enqueue=True,  # file writes in a background thread
    )

# --------------------------------------------------------------------------- #
# 3. Expose *the* singleton logger for imports elsewhere
# --------------------------------------------------------------------------- #
logger = _logger


def scrub_headers(headers: dict[str, str]) -> dict[str, str]:
    headers = headers.copy()
    if "X-API-Key" in headers:
        headers["X-API-Key"] = "<redacted>"
    if "Authorization" in headers:
        headers["Authorization"] = "<redacted>"
    return headers