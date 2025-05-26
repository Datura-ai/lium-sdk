from uuid import UUID
from celium.models.ssh_key import SSHKey
from celium.resources.base import BaseAsyncResource
from celium.resources.ssh_keys.base import _SSHKeysCore

class AsyncSSHKeys(BaseAsyncResource, _SSHKeysCore):
    """
    Async/await version of the SSHKeys resource.
    """
    async def create(self, name: str, public_key: str) -> SSHKey:
        """
        Create an SSH key.

        :param name: The name of the SSH key.
        :type name: str
        :param public_key: The public key string.
        :type public_key: str
        :return: The created SSHKey object.
        :rtype: SSHKey
        """
        resp = await self._t.arequest(
            "POST", self.list_url, json={"name": name, "public_key": public_key}
        )
        return self.parse_one(self._get_json(resp))

    async def update(self, id: UUID, name: str, public_key: str) -> SSHKey:
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
        resp = await self._t.arequest(
            "PUT", f"{self.list_url}{id}", json={"name": name, "public_key": public_key}
        )
        return self.parse_one(self._get_json(resp))

    async def list(self) -> list[SSHKey]:
        """
        List all SSH keys for the current user.

        :return: A list of SSHKey objects.
        :rtype: list[SSHKey]
        """
        resp = await self._t.arequest("GET", f"{self.list_url}/me")
        return self.parse_many(self._get_json(resp))

    async def delete(self, id: UUID) -> None:
        """
        Delete an SSH key.

        :param id: The UUID of the SSH key to delete.
        :type id: UUID
        :return: None
        :rtype: None
        """
        await self._t.arequest("DELETE", f"{self.list_url}{id}")
