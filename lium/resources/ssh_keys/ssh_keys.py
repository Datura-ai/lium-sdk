from uuid import UUID
from lium.models.ssh_key import SSHKey
from lium.resources.base import BaseResource
from lium.resources.ssh_keys.base import _SSHKeysCore

class SSHKeys(BaseResource, _SSHKeysCore):
    """
    Resource to manage SSH keys.
    """
    def create(self, name: str, public_key: str) -> SSHKey:
        """
        Create an SSH key.

        :param name: The name of the SSH key.
        :type name: str
        :param public_key: The public key string.
        :type public_key: str
        :return: The created SSHKey object.
        :rtype: SSHKey
        """
        resp = self._t.request(
            "POST", self.list_url, json={"name": name, "public_key": public_key}
        )
        return self.parse_one(self._get_json(resp))

    def update(self, id: UUID, name: str, public_key: str) -> SSHKey:
        """
        Update an SSH key.

        :param id: The UUID of the SSH key to update.
        :type id: UUID
        :param name: The new name of the SSH key.
        :type name: str
        :param public_key: The new public key string.
        :type public_key: str
        :return: The updated SSHKey object.
        :rtype: SSHKey
        """
        resp = self._t.request(
            "PUT", f"{self.list_url}{id}", json={"name": name, "public_key": public_key}
        )
        return self.parse_one(self._get_json(resp))

    def list(self) -> list[SSHKey]:
        """
        List all SSH keys for the current user.

        :return: A list of SSHKey objects.
        :rtype: list[SSHKey]
        """
        resp = self._t.request("GET", f"{self.list_url}/me")
        return self.parse_many(self._get_json(resp))

    def delete(self, id: UUID) -> None:
        """
        Delete an SSH key.

        :param id: The UUID of the SSH key to delete.
        :type id: UUID
        :return: None
        :rtype: None
        """
        self._t.request("DELETE", f"{self.list_url}{id}")
