from uuid import UUID
from lium.models.docker_credentials import DockerCredential
from lium.resources.base import BaseAsyncResource
from lium.resources.docker_credentials.docker_credentials_core import _DockerCredentialsCore


class AsyncDockerCredentials(BaseAsyncResource, _DockerCredentialsCore):
    """Async/await version of the DockerCredentials resource."""
    
    async def create(self, username: str, password: str) -> DockerCredential:
        """
        Create a docker credential.

        :param username: Docker registry username.
        :type username: str
        :param password: Docker registry password.
        :type password: str
        :return: The created DockerCredential object.
        :rtype: DockerCredential
        """
        resp = await self._t.arequest(
            "POST", self.list_url, json={"docker_username": username, "docker_password": password}
        )
        return self.parse_one(self._get_json(resp))
    
    async def update(self, id: UUID, username: str, password: str) -> DockerCredential:
        """
        Update a docker credential.

        :param id: The UUID of the docker credential to update.
        :type id: UUID
        :param username: New docker registry username.
        :type username: str
        :param password: New docker registry password.
        :type password: str
        :return: The updated DockerCredential object.
        :rtype: DockerCredential
        """
        resp = await self._t.arequest(
            "PUT", f"{self.list_url}{id}", json={"docker_username": username, "docker_password": password}
        )
        return self.parse_one(self._get_json(resp))

    async def list(self) -> list[DockerCredential]:
        """
        List all docker credentials.

        Docker credentials are used to authenticate with a docker registry.

        :return: List of docker credentials.
        :rtype: list[DockerCredential]
        """
        resp = await self._t.arequest("GET", self.list_url)
        return self.parse_many(self._get_json(resp))
    
    async def delete(self, id: UUID) -> None:
        """
        Delete a docker credential.

        :param id: The UUID of the docker credential to delete.
        :type id: UUID
        :return: None
        :rtype: None
        """
        await self._t.arequest("DELETE", f"{self.list_url}{id}")

    async def get_default(self) -> DockerCredential:
        """
        Get the default docker credential.

        :return: The default DockerCredential object. If none exists, a new one is created and returned.
        :rtype: DockerCredential
        """
        d_creds = await self.list()
        if len(d_creds) > 0:
            return d_creds[0]
        # Create a new docker credential
        resp = await self._t.arequest("POST", self.list_url)
        return self.parse_one(self._get_json(resp))