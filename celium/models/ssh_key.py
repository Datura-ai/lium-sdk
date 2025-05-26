from datetime import datetime
from uuid import UUID
from celium.models import _FrozenBase


class _SSHKeyBase(_FrozenBase):
    name: str
    public_key: str


class SSHKeyCreate(_SSHKeyBase):
    pass


class SSHKey(_SSHKeyBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime