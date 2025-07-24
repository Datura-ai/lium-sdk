"""Typed request / response bodies."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class _FrozenBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
