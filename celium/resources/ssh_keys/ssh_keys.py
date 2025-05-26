from uuid import UUID
from celium.models.ssh_key import SSHKey
from celium.resources.base import BaseResource
from celium.resources.ssh_keys.base import _SSHKeysCore

class SSHKeys(BaseResource, _SSHKeysCore):
    def create(self, name: str, public_key: str) -> SSHKey:
        resp = self._t.request(
            "POST", self.list_url, json={"name": name, "public_key": public_key}
        )
        return self.parse_one(self._get_json(resp))

    def update(self, id: UUID, name: str, public_key: str) -> SSHKey:
        resp = self._t.request(
            "PUT", f"{self.list_url}{id}", json={"name": name, "public_key": public_key}
        )
        return self.parse_one(self._get_json(resp))

    def list(self) -> list[SSHKey]:
        resp = self._t.request("GET", f"{self.list_url}/me")
        return self.parse_many(self._get_json(resp))

    def delete(self, id: UUID) -> None:
        self._t.request("DELETE", f"{self.list_url}{id}")
