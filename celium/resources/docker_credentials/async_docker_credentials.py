from uuid import UUID
from celium.models.docker_credentials import DockerCredential
from celium.resources.base import BaseAsyncResource
from celium.resources.docker_credentials.docker_credentials_core import _DockerCredentialsCore


class AsyncDockerCredentials(BaseAsyncResource, _DockerCredentialsCore):
    async def create(self, username: str, password: str) -> DockerCredential:
        """Create a docker credential.
        """
        resp = await self._t.arequest(
            "POST", self.list_url, json={"docker_username": username, "docker_password": password}
        )
        return self.parse_one(self._get_json(resp))
    
    async def update(self, id: UUID, username: str, password: str) -> DockerCredential:
        """Update a docker credential.
        """
        resp = await self._t.arequest(
            "PUT", f"{self.list_url}{id}", json={"docker_username": username, "docker_password": password}
        )
        return self.parse_one(self._get_json(resp))

    async def list(self) -> list[DockerCredential]:
        """List all docker credentials.
        Docker credentials are used to authenticate with a docker registry.

        Returns:
            list[DockerCredential]: List of docker credentials.
        """
        resp = await self._t.arequest("GET", self.list_url)
        return self.parse_many(self._get_json(resp))
    
    async def delete(self, id: UUID) -> None:
        """Delete a docker credential.
        """
        await self._t.arequest("DELETE", f"{self.list_url}{id}")
