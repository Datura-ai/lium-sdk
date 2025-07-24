from datetime import datetime
from typing import Literal
from uuid import UUID
from lium.models import _FrozenBase
from lium.models.executor import ExecutorStatus, ExecutorForPod
from lium.models.template import TemplateForPod


class _PodBase(_FrozenBase):
    ports_mapping: dict | str
    pod_name: str
    ssh_connect_cmd: str
    gpu_name: str
    gpu_count: str
    cpu_name: str
    ram_total: int
    status: Literal["RUNNING", "STOPPED", "FAILED", "PENDING", "DELETING"]
    is_favorite: bool | None
    updated_at: datetime
    created_at: datetime


class PodList(_PodBase):
    id: UUID
    template: TemplateForPod
    executor: ExecutorForPod


class Pod(PodList):
    executor_status: ExecutorStatus | None = None
