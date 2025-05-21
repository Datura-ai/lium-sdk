"""/containers endpoints."""
from __future__ import annotations
from typing import Any, Iterable, Iterator, List

from .base import BaseResource


class Pods(BaseResource):
    ENDPOINT = "/pods"

    # ---------------- CRUD ---------------- #
    # def create(
    #     self,
    #     *,
    #     image: str,
    #     gpu_type: str,
    #     volume_size_gb: int,
    #     name: str | None = None,
    # ) -> Container:
    #     body = {
    #         "image": image,
    #         "gpu_type": gpu_type,
    #         "volume_size_gb": volume_size_gb,
    #         "name": name,
    #     }
    #     resp = self._t.request("POST", self.ENDPOINT, json=body)
    #     return Container.model_validate(self._get_json(resp))

    # def list(
    #     self, *, status: str | None = None, limit: int = 100
    # ) -> list[Container]:
    #     params = {"status": status, "limit": limit}
    #     resp = self._t.request("GET", self.ENDPOINT, params=params)
    #     return [Container.model_validate(r) for r in self._get_json(resp)["items"]]

    # def delete(self, container_id: str) -> None:
    #     self._t.request("DELETE", f"{self.ENDPOINT}/{container_id}")
