from uuid import UUID
from lium.models.docker_credentials import DockerCredential
from lium.resources.base import BaseResource
from lium.resources.docker_credentials.docker_credentials_core import _DockerCredentialsCore


class DockerCredentials(BaseResource, _DockerCredentialsCore):
    """
    Docker credentials are used to authenticate with a docker registry.
    """
    def create(self, username: str, password: str) -> DockerCredential:
        """
        Create a docker credential.

        :param username: Docker registry username.
        :type username: str
        :param password: Docker registry password.
        :type password: str
        :return: The created DockerCredential object.
        :rtype: DockerCredential
        """
        resp = self._t.request(
            "POST", self.list_url, json={"docker_username": username, "docker_password": password}
        )
        return self.parse_one(self._get_json(resp))
    
    def update(self, id: UUID, username: str, password: str) -> DockerCredential:
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
        resp = self._t.request(
            "PUT", f"{self.list_url}{id}", json={"docker_username": username, "docker_password": password}
        )
        return self.parse_one(self._get_json(resp))

    def list(self) -> list[DockerCredential]:
        """
        List all docker credentials.

        Docker credentials are used to authenticate with a docker registry.

        :return: List of docker credentials.
        :rtype: list[DockerCredential]
        """
        resp = self._t.request("GET", self.list_url)
        return self.parse_many(self._get_json(resp))

    def delete(self, id: UUID) -> None:
        """
        Delete a docker credential.

        :param id: The UUID of the docker credential to delete.
        :type id: UUID
        :return: None
        :rtype: None
        """
        self._t.request("DELETE", f"{self.list_url}{id}")

    def get_default(self) -> DockerCredential:
        """
        Get the default docker credential.

        :return: The default DockerCredential object. If none exists, a new one is created and returned.
        :rtype: DockerCredential
        """
        d_creds = self.list()
        if len(d_creds) > 0:
            return d_creds[0]
        # Create a new docker credential
        resp = self._t.request("POST", self.list_url)
        return self.parse_one(self._get_json(resp))
