"""Lightweight, dependency-free retry helper (sync only)."""
from __future__ import annotations
import time
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def retry(
    attempts: int = 3,
    backoff_factor: float = 0.5,
    allowed: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """`@retry(attempts=3)` decorator with exponential back-off."""

    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            delay = backoff_factor
            for attempt in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except allowed as exc:
                    if attempt == attempts - 1:
                        raise
                    time.sleep(delay)
                    delay *= 2

        return wrapper

    return decorator
