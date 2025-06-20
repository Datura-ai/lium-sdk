from __future__ import annotations
from uuid import UUID
from . import _FrozenBase


class Location(_FrozenBase):
    country: str
    country_code: str | None
    region: str | None
    region_name: str | None
    city: str | None
    zip: str | None
    lat: float | None
    lon: float | None
    timezone: str

class GpuDetail(_FrozenBase):
    name: str
    cuda: str
    power_limit: int
    graphics_speed: int
    memory_speed: int
    pcie: int | None = None
    pcie_speed: int | None = None
    capacity: int
    gpu_utilization: float | None = None
    memory_utilization: float | None = None
    uuid: str | None = None


class GpuSpec(_FrozenBase):
    count: int
    driver: str | None = None
    cuda_driver: int | None = None
    details: list[GpuDetail]


class CpuSpec(_FrozenBase):
    count: int
    model: str
    utilization: float | None = None


class MemorySpec(_FrozenBase):
    total: float
    used: float
    free: float
    available: float | None = None
    utilization: float | None = None


class NetworkSpec(_FrozenBase):
    upload_speed: float | None = None
    download_speed: float | None = None


class HardDiskSpec(_FrozenBase):
    total: int
    used: int
    free: int
    utilization: float | None = None


class Checksums(_FrozenBase):
    nvidia_smi: str | None = None
    libnvidia_ml: str | None = None
    docker: str | None = None


class DockerSpec(_FrozenBase):
    version: str | None = None
    container_id: str | None = None
    containers: list[dict] | None = None


class MachineSpec(_FrozenBase):
    gpu: GpuSpec
    cpu: CpuSpec
    ram: MemorySpec
    hard_disk: HardDiskSpec | None = None
    os: str | None = None
    network: NetworkSpec | None = None
    md5_checksums: Checksums | None = None
    docker: DockerSpec | None = None
    gpu_processes: list[dict] | None = None
    available_port_maps: list[tuple[int, int]] | None = None
    sysbox_runtime: bool | None = None


class ExecutorFilterQuery(_FrozenBase):
    machine_names: list[str] | None = None
    price_per_hour_lte: float | None = None
    price_per_hour_gte: float | None = None
    gpu_count_lte: int | None = None
    gpu_count_gte: int | None = None


class _ExecutorBase(_FrozenBase):
    id: UUID
    machine_name: str
    price_per_hour: float
    executor_ip_address: str
    validator_hotkey: str
    specs: MachineSpec
    uptime_in_minutes: int | None


class Executor(_ExecutorBase):
    location: Location | None


class ExecutorForPod(_ExecutorBase):
    active: bool


class ExecutorStatus(_FrozenBase):
    logs: list[dict]
    

class DockerImageInfo(_FrozenBase):
  docker_image: str
  docker_image_tag: str
  docker_image_size: int