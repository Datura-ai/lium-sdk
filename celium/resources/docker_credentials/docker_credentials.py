from uuid import UUID
from celium.models.docker_credentials import DockerCredential
from celium.resources.base import BaseResource
from celium.resources.docker_credentials.docker_credentials_core import _DockerCredentialsCore


class DockerCredentials(BaseResource, _DockerCredentialsCore):
    def create(self, username: str, password: str) -> DockerCredential:
        """Create a docker credential.
        """
        resp = self._t.request(
            "POST", self.list_url, json={"docker_username": username, "docker_password": password}
        )
        return self.parse_one(self._get_json(resp))
    
    def update(self, id: UUID, username: str, password: str) -> DockerCredential:
        """Update a docker credential.
        """
        resp = self._t.request(
            "PUT", f"{self.list_url}{id}", json={"docker_username": username, "docker_password": password}
        )
        return self.parse_one(self._get_json(resp))

    def list(self) -> list[DockerCredential]:
        """List all docker credentials.
        Docker credentials are used to authenticate with a docker registry.

        Returns:
            list[DockerCredential]: List of docker credentials.
        """
        resp = self._t.request("GET", self.list_url)
        return self.parse_many(self._get_json(resp))

    def delete(self, id: UUID) -> None:
        """Delete a docker credential.
        """
        self._t.request("DELETE", f"{self.list_url}/{id}")
