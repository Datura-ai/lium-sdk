from datetime import datetime
from uuid import UUID
from typing_extensions import Literal
from lium.models import _FrozenBase


class TemplateBase(_FrozenBase):
    name: str
    description: str | None = None
    docker_image: str
    docker_image_tag: str
    docker_image_digest: str | None = ""
    docker_image_size: int | None = None
    category: Literal["DOCKER", "PYTORCH", "NVIDIA", "TENSOR_FLOW", "OPEN_AI", "UBUNTU"] = "DOCKER"
    volumes: list[str] | None = ["/workspace"]
    environment: dict[str, str] | None = {}
    entrypoint: str | None = ""
    internal_ports: list[int] | None = []
    is_private: bool = True
    readme: str | None = None
    startup_commands: str | None = ""



class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(TemplateBase):
    pass


class TemplateForPod(TemplateBase):
    pass


class Template(TemplateBase):
    id: UUID
    user_id: UUID | None 
    status: Literal["CREATED", "UPDATED", "VERIFY_PENDING", "VERIFY_FAILED", "VERIFY_SUCCESS"] = "CREATED"
    docker_credential_id: UUID | None = None
    verification_logs: str | None = None
    container_start_immediately: bool | None = True
    created_at: datetime
    updated_at: datetime
