from uuid import UUID
from datetime import datetime
from lium.models import _FrozenBase


class DockerCredential(_FrozenBase):
    id: UUID
    user_id: UUID
    username: str
    password: str
    created_at: datetime
    updated_at: datetime
    