from typing import Any
from celium.models.ssh_key import SSHKey

class _SSHKeysCore:
    ENDPOINT = "/ssh-keys"

    def parse_many(self, data: list[dict[str, Any]]) -> list[SSHKey]:
        return [SSHKey.model_validate(r) for r in data]
    
    def parse_one(self, data: dict[str, Any]) -> SSHKey:
        return SSHKey.model_validate(data)

    @property
    def list_url(self) -> str:
        return f"{self.ENDPOINT}"
