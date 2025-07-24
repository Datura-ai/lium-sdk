from typing import Any
from lium.models.docker_credentials import DockerCredential


class _DockerCredentialsCore:
    ENDPOINT = "/docker-credentials"

    def parse_many(self, data: list[dict[str, Any]]) -> list[DockerCredential]:
        return [DockerCredential.model_validate(r) for r in data]
    
    def parse_one(self, data: dict[str, Any]) -> DockerCredential:
        return DockerCredential.model_validate(data)

    @property
    def list_url(self) -> str:
        return f"{self.ENDPOINT}/"