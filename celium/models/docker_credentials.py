from uuid import UUID
from datetime import datetime
from celium.models import _FrozenBase


class DockerCredential(_FrozenBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    