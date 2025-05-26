from uuid import UUID
from celium.models.ssh_key import SSHKey
from celium.resources.base import BaseAsyncResource
from celium.resources.ssh_keys.base import _SSHKeysCore

class AsyncSSHKeys(BaseAsyncResource, _SSHKeysCore):
    async def create(self, name: str, public_key: str) -> SSHKey:
        resp = await self._t.arequest(
            "POST", self.list_url, json={"name": name, "public_key": public_key}
        )
        return self.parse_one(self._get_json(resp))

    async def update(self, id: UUID, name: str, public_key: str) -> SSHKey:
        resp = await self._t.arequest(
            "PUT", f"{self.list_url}{id}", json={"name": name, "public_key": public_key}
        )
        return self.parse_one(self._get_json(resp))

    async def list(self) -> list[SSHKey]:
        resp = await self._t.arequest("GET", self.list_url)
        return self.parse_many(self._get_json(resp))

    async def delete(self, id: UUID) -> None:
        await self._t.arequest("DELETE", f"{self.list_url}{id}")
