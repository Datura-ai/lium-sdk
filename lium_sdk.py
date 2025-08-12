"""Lium SDK - Clean, Unix-style SDK for GPU pod management."""

import hashlib
import os
import random
import re
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

import paramiko
import requests
from dotenv import load_dotenv

load_dotenv()

# Constants
ADJECTIVES = ["swift", "brave", "calm", "eager", "gentle", "cosmic", "golden", "lunar", "zesty", "noble"]
NOUNS = ["hawk", "lion", "eagle", "fox", "wolf", "shark", "raven", "matrix", "comet", "orbit"]


# Exceptions
class LiumError(Exception):
    """Base exception for Lium SDK."""

class LiumAuthError(LiumError):
    """Authentication error."""

class LiumRateLimitError(LiumError):
    """Rate limit exceeded."""

class LiumServerError(LiumError):
    """Server error."""

# Data Models
@dataclass
class ExecutorInfo:
    id: str
    huid: str
    machine_name: str
    gpu_type: str
    gpu_count: int
    price_per_hour: float
    price_per_gpu_hour: float
    location: Dict
    specs: Dict
    status: str
    docker_in_docker: bool


@dataclass
class PodInfo:
    id: str
    name: str
    status: str
    huid: str
    ssh_cmd: Optional[str]
    ports: Dict
    created_at: str
    updated_at: str
    executor: Optional[ExecutorInfo]
    template: Dict

    @property
    def host(self) -> Optional[str]:
        return (re.findall(r'@(\S+)', self.ssh_cmd) or [None])[0] if self.ssh_cmd else None

    @property
    def username(self) -> Optional[str]:
        return (re.findall(r'ssh (\S+)@', self.ssh_cmd) or [None])[0] if self.ssh_cmd else None

    @property
    def ssh_port(self) -> int:
        """Extract SSH port from command."""
        if not self.ssh_cmd or '-p ' not in self.ssh_cmd:
            return 22
        return int(self.ssh_cmd.split('-p ')[1].split()[0])

@dataclass
class Template:
    """Template information."""
    id: str
    name: str
    huid: str
    docker_image: str
    docker_image_tag: str
    category: str
    status: str


@dataclass
class Config:
    api_key: str
    base_url: str = "https://lium.io/api"
    base_pay_url: str = "https://pay-api.lium.io"
    ssh_key_path: Optional[Path] = None

    @classmethod
    def load(cls) -> "Config":
        """Load config from env/file with smart defaults."""
        api_key = os.getenv("LIUM_API_KEY")
        if not api_key:
            from configparser import ConfigParser
            config_file = Path.home() / ".lium" / "config.ini"
            if config_file.exists():
                config = ConfigParser()
                config.read(config_file)
                api_key = config.get("api", "api_key", fallback=None)

        if not api_key:
            raise ValueError("No API key found. Set LIUM_API_KEY or ~/.lium/config.ini")

        # Find SSH key with fallback
        ssh_key = None
        for key_name in ["id_ed25519", "id_rsa", "id_ecdsa"]:
            key_path = Path.home() / ".ssh" / key_name
            if key_path.exists():
                ssh_key = key_path
                break

        return cls(
            api_key=api_key,
            base_url=os.getenv("LIUM_BASE_URL", "https://lium.io/api"),
            base_pay_url=os.getenv("LIUM_PAY_URL", "https://pay-api.lium.io"),
            ssh_key_path=ssh_key
        )

    @property
    def ssh_public_keys(self) -> List[str]:
        """Get SSH public keys."""
        if not self.ssh_key_path:
            return []
        pub_path = self.ssh_key_path.with_suffix('.pub')
        if pub_path.exists():
            with open(pub_path) as f:
                return [l.strip() for l in f if l.strip().startswith(('ssh-', 'ecdsa-'))]
        return []

# Helper Functions
def generate_huid(id_str: str) -> str:
    """Generate human-readable ID from UUID."""
    if not id_str:
        return "invalid"

    digest = hashlib.md5(id_str.encode()).hexdigest()
    adj = ADJECTIVES[int(digest[:4], 16) % len(ADJECTIVES)]
    noun = NOUNS[int(digest[4:8], 16) % len(NOUNS)]
    return f"{adj}-{noun}-{digest[-2:]}"

def extract_gpu_type(machine_name: str) -> str:
    """Extract GPU type from machine name."""
    patterns = [
        (r"RTX\s*(\d{4})", lambda m: f"RTX{m.group(1)}"),
        (r"([HBL])(\d{2,3}S?)", lambda m: f"{m.group(1)}{m.group(2)}"),
        (r"A(\d{2,4})", lambda m: f"A{m.group(1)}"),
    ]
    for pattern, fmt in patterns:
        if match := re.search(pattern, machine_name, re.I):
            return fmt(match)
    return machine_name.split()[-1] if machine_name else "Unknown"

def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """Retry decorator for API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (LiumRateLimitError, LiumServerError, requests.RequestException):
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (2 ** attempt) + random.uniform(0, 0.5))
        return wrapper
    return decorator

# Main SDK Class
class Lium:
    """Clean Unix-style SDK for Lium."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.headers = {"X-API-KEY": self.config.api_key}
        self._pods_cache = {}

    @with_retry()
    def _request(
        self,
        method: str,
        endpoint: str,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> requests.Response:
        """Make API request with error handling."""
        url = f"{base_url or self.config.base_url}/{endpoint.lstrip('/')}"
        request_headers = headers or self.headers
        resp = requests.request(method, url, headers=request_headers, timeout=30, **kwargs)

        if resp.ok:
            return resp

        # Map errors
        if resp.status_code == 401:
            raise LiumAuthError("Invalid API key")
        if resp.status_code == 429:
            raise LiumRateLimitError("Rate limit exceeded")
        if 500 <= resp.status_code < 600:
            raise LiumServerError(f"Server error: {resp.status_code}")
        raise LiumError(f"API error {resp.status_code}: {resp.text}")

    def _dict_to_executor_info(self, executor_dict: Dict) -> Optional[ExecutorInfo]:
        """Convert executor dict to ExecutorInfo object."""
        if not executor_dict:
            return None

        # Extract GPU info from specs or machine_name
        specs = executor_dict.get("specs", {})
        gpu_info = specs.get("gpu", {})
        gpu_count = gpu_info.get("count", 1)

        # Extract GPU type from machine_name or specs
        machine_name = executor_dict.get("machine_name", "")
        gpu_type = extract_gpu_type(machine_name)

        # If we couldn't extract from machine_name, try specs
        if gpu_type == machine_name.split()[-1] and gpu_info.get("details"):
            gpu_details = gpu_info.get("details", [])
            if gpu_details:
                gpu_name = gpu_details[0].get("name", "")
                if gpu_name:
                    gpu_type = extract_gpu_type(gpu_name)

        price_per_hour = executor_dict.get("price_per_hour", 0)

        return ExecutorInfo(
            id=executor_dict.get("id", ""),
            huid=generate_huid(executor_dict.get("id", "")),
            machine_name=machine_name,
            gpu_type=gpu_type,
            gpu_count=gpu_count,
            price_per_hour=price_per_hour,
            price_per_gpu_hour=price_per_hour / max(1, gpu_count),
            location=executor_dict.get("location", {}),
            specs=specs,
            status=executor_dict.get("status", "unknown"),
            docker_in_docker=specs.get("sysbox_runtime", False)
        )

    def ls(self, gpu_type: Optional[str] = None) -> List[ExecutorInfo]:
        """List available executors."""
        data = self._request("GET", "/executors").json()
        executors = [self._dict_to_executor_info(d) for d in data]
        executors = [e for e in executors if e]  # Filter None values

        if gpu_type:
            executors = [e for e in executors if e.gpu_type.upper() == gpu_type.upper()]

        return executors

    def ps(self) -> List[PodInfo]:
        """List active pods."""
        data = self._request("GET", "/pods").json()

        pods = [
            PodInfo(
                id=d.get("id", ""),
                name=d.get("pod_name", ""),
                status=d.get("status", "unknown"),
                huid=generate_huid(d.get("id", "")),
                ssh_cmd=d.get("ssh_connect_cmd"),
                ports=d.get("ports_mapping", {}),
                created_at=d.get("created_at", ""),
                updated_at=d.get("updated_at", ""),
                executor=self._dict_to_executor_info(d.get("executor", {})) if d.get("executor") else None,
                template=d.get("template", {})
            )
            for d in data
        ]

        # Update cache for resolution
        self._pods_cache = {p.id: p for p in pods}
        for p in pods:
            self._pods_cache[p.name] = p
            self._pods_cache[p.huid] = p

        return pods

    def templates(self, filter: Optional[str] = None, only_my: bool = False) -> List[Template]:
        """List available templates (Unix-style: like 'ls' for templates)."""
        data = self._request("GET", "/templates").json()

        if only_my:
            user_id = self.get_my_user_id()
            data = [d for d in data if d.get("user_id") == user_id]

        templates = [
            Template(
                id=d.get("id", ""),
                huid=generate_huid(d.get("id", "")),
                name=d.get("name", ""),
                docker_image=d.get("docker_image", ""),
                docker_image_tag=d.get("docker_image_tag", "latest"),
                category=d.get("category", "general"),
                status=d.get("status", "unknown"),
            )
            for d in data
        ]
        if filter:
            filter_lower = filter.lower()
            templates = [
                t for t in templates
                if filter_lower in t.docker_image.lower() or filter_lower in t.name.lower()
            ]

        return templates

    def up(self, executor_id: str, pod_name: Optional[str] = None, 
           template_id: Optional[str] = None) -> Dict[str, Any]:
        """Start a new pod."""
        if not template_id:
            available = self.templates()
            if not available:
                raise ValueError("No templates available")
            template_id = available[0].id

        ssh_keys = self.config.ssh_public_keys
        if not ssh_keys:
            raise ValueError("No SSH keys found")

        payload = {
            "pod_name": pod_name,
            "template_id": template_id,
            "user_public_key": ssh_keys
        }

        response = self._request("POST", f"/executors/{executor_id}/rent", json=payload).json()

        # API should return pod info
        if response and "id" in response:
            return response

        # Fallback: find pod by name after creation
        if pod_name:
            for _ in range(2):
                time.sleep(3)
                for pod in self.ps():
                    if pod.name == pod_name:
                        return {
                            "id": pod.id,
                            "name": pod.name,
                            "status": pod.status,
                            "huid": pod.huid,
                            "ssh_cmd": pod.ssh_cmd,
                            "executor_id": executor_id
                        }

        raise LiumError(f"Failed to create pod{' ' + pod_name if pod_name else ''}")

    def down(self, pod: Union[str, PodInfo]) -> Dict[str, Any]:
        """Stop a pod."""
        pod_info = self._resolve_pod(pod)

        if not pod_info.executor:
            raise ValueError(f"No executor info for pod {pod_info.name}")

        return self._request("DELETE", f"/executors/{pod_info.executor.id}/rent").json()

    def rm(self, pod: Union[str, PodInfo]) -> Dict[str, Any]:
        """Remove pod (alias for down)."""
        return self.down(pod)

    def _resolve_pod(self, pod: Union[str, PodInfo]) -> PodInfo:
        """Resolve pod by ID, name, or HUID."""
        if isinstance(pod, PodInfo):
            return pod

        # Check cache first
        if pod in self._pods_cache:
            return self._pods_cache[pod]

        # Refresh and search
        for p in self.ps():
            if p.id == pod or p.name == pod or p.huid == pod:
                return p

        raise ValueError(f"Pod '{pod}' not found")

    def get_executor(self, executor: Union[str, ExecutorInfo]) -> Optional[ExecutorInfo]:
        """Get executor by ID or HUID."""
        if isinstance(executor, ExecutorInfo):
            return executor

        # Search in current executors
        for e in self.ls():
            if e.id == executor or e.huid == executor:
                return e

        return None

    def get_template(self, template_id: Optional[str] = None) -> Optional[Template]:
        """Get template ID, auto-selecting if None."""
        templates = self.templates()
        for t in templates:
            if t.id == template_id or t.huid == template_id or t.name == template_id:
                return t
        return None

    @contextmanager
    def ssh_connection(self, pod: Union[str, PodInfo], timeout: int = 30):
        """SSH connection context manager."""
        pod_info = self._resolve_pod(pod)

        if not pod_info.ssh_cmd:
            raise ValueError(f"No SSH for pod {pod_info.name}")

        if not self.config.ssh_key_path:
            raise ValueError("No SSH key configured")

        # Parse SSH command
        parts = shlex.split(pod_info.ssh_cmd)
        user_host = parts[1]
        user, host = user_host.split("@")
        port = pod_info.ssh_port

        # Load SSH key
        key = None
        for key_type in [paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey]:
            try:
                key = key_type.from_private_key_file(str(self.config.ssh_key_path))
                break
            except (paramiko.SSHException, FileNotFoundError, PermissionError):
                continue

        if not key:
            raise ValueError("Could not load SSH key")

        # Connect
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=port, username=user, pkey=key, timeout=timeout)

        try:
            yield client
        finally:
            client.close()

    def _prep_command(self, command: str, env: Optional[Dict[str, str]] = None) -> str:
        """Prepare command with environment variables."""
        if env:
            env_str = " && ".join([f'export {k}="{v}"' for k, v in env.items()])
            return f"{env_str} && {command}"
        return command

    def exec(self, pod: Union[str, PodInfo], command: str, 
             env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute command on pod."""
        command = self._prep_command(command, env)

        with self.ssh_connection(pod) as client:
            stdin, stdout, stderr = client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            return {
                "stdout": stdout.read().decode("utf-8", errors="replace"),
                "stderr": stderr.read().decode("utf-8", errors="replace"),
                "exit_code": exit_code,
                "success": exit_code == 0
            }

    def stream_exec(self, pod: Union[str, PodInfo], command: str,
                    env: Optional[Dict[str, str]] = None) -> Generator[Dict[str, str], None, None]:
        """Execute command with streaming output."""
        command = self._prep_command(command, env)

        with self.ssh_connection(pod) as client:
            stdin, stdout, stderr = client.exec_command(command, get_pty=True)
            stdin.close()

            channel = stdout.channel
            channel.settimeout(0.1)

            while not channel.closed or channel.recv_ready() or channel.recv_stderr_ready():
                if channel.recv_ready():
                    data = channel.recv(4096).decode("utf-8", errors="replace")
                    if data:
                        yield {"type": "stdout", "data": data}

                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                    if data:
                        yield {"type": "stderr", "data": data}

    def exec_all(self, pods: List[Union[str, PodInfo]], command: str,
                 env: Optional[Dict[str, str]] = None, max_workers: int = 10) -> List[Dict]:
        """Execute command on multiple pods in parallel."""
        def exec_single(pod):
            try:
                result = self.exec(pod, command, env)
                result["pod"] = pod.id if isinstance(pod, PodInfo) else pod
                return result
            except Exception as e:
                return {"pod": pod, "error": str(e), "success": False}

        with ThreadPoolExecutor(max_workers=min(max_workers, len(pods))) as executor:
            return list(executor.map(exec_single, pods))

    def wait_ready(self, pod: Union[str, PodInfo, Dict], timeout: int = 300) -> Optional[PodInfo]:
        """Wait for pod to be ready."""
        if isinstance(pod, PodInfo):
            pod_id = pod.id
        elif isinstance(pod, dict) and 'id' in pod:
            pod_id = pod['id']
        else:
            pod_id = pod

        start = time.time()
        while time.time() - start < timeout:
            fresh_pods = self.ps()
            current = next((p for p in fresh_pods if p.id == pod_id), None)

            if current and current.status.upper() == "RUNNING" and current.ssh_cmd:
                return current

            time.sleep(10)
        return None

    def scp(self, pod: Union[str, PodInfo], local: str, remote: str) -> None:
        """Upload file to pod."""
        with self.ssh_connection(pod) as client:
            sftp = client.open_sftp()
            sftp.put(local, remote)
            sftp.close()

    def download(self, pod: Union[str, PodInfo], remote: str, local: str) -> None:
        """Download file from pod."""
        with self.ssh_connection(pod) as client:
            sftp = client.open_sftp()
            sftp.get(remote, local)
            sftp.close()

    def upload(self, pod: Union[str, PodInfo], local: str, remote: str) -> None:
        """Upload file to pod."""
        self.scp(pod, local, remote)

    def ssh(self, pod: Union[str, PodInfo]) -> str:
        """Get SSH command string."""
        pod_info = self._resolve_pod(pod)
        if not pod_info.ssh_cmd or not self.config.ssh_key_path:
            raise ValueError("No SSH configured")

        return pod_info.ssh_cmd.replace("ssh ", f"ssh -i {self.config.ssh_key_path} ")

    def rsync(self, pod: Union[str, PodInfo], local: str, remote: str) -> None:
        """Sync directories with rsync."""
        pod_info = self._resolve_pod(pod)
        if not pod_info.ssh_cmd or not self.config.ssh_key_path:
            raise ValueError("No SSH configured")

        ssh_cmd = f"ssh -i {self.config.ssh_key_path} -p {pod_info.ssh_port} -o StrictHostKeyChecking=no"
        cmd = ["rsync", "-avz", "-e", ssh_cmd, local,  f"{pod_info.username}@{pod_info.host}:{remote}"]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Rsync failed: {result.stderr}")

    
    def create_template(
        self,
        name: str,
        docker_image: str,
        docker_image_digest: str,
        docker_image_tag: str = "latest",
        ports: Optional[List[int]] = None,
        start_command: Optional[str] = None,
        **kwargs
    ) -> Template:
        """Create a new template."""
        payload = {
            "name": name,
            "docker_image": docker_image,
            "docker_image_digest": docker_image_digest,
            "docker_image_tag": docker_image_tag,
            "internal_ports": ports or [22, 8000],
            "startup_commands": start_command or "",
            "category": kwargs.get("category", "UBUNTU"),
            "container_start_immediately": kwargs.get("container_start_immediately", True),
            "description": kwargs.get("description", name),
            "entrypoint": kwargs.get("entrypoint", ""),
            "environment": kwargs.get("environment", {}),
            "is_private": kwargs.get("is_private", False),
            "readme": kwargs.get("readme", name),
            "volumes": kwargs.get("volumes", []),
        }

        response = self._request("POST", "/templates", json=payload).json()
        return Template(
            id=response.get("id", ""),
            huid=generate_huid(response.get("id", "")),
            name=response.get("name", ""),
            docker_image=response.get("docker_image", ""),
            docker_image_tag=response.get("docker_image_tag", "latest"),
            category=response.get("category", "general"),
            status=response.get("status", "unknown"),
        )

    def wait_template_ready(self, template_id: str, timeout: int = 300) -> Optional[Template]:
        """Wait for template to be ready."""

        start = time.time()
        while time.time() - start < timeout:
            templates = self.templates()
            current = next((t for t in templates if t.id == template_id), None)

            if current:
                status = current.status.upper()
                if status == "VERIFY_SUCCESS":
                    return current
                elif status == "VERIFY_FAILED":
                    raise LiumError(f"Template verification failed: {current.name}")

            time.sleep(10)
        return None

    def get_my_user_id(self) -> str:
        """Get current user ID."""
        return self._request("GET", "/users/me").json()["id"]

    def update_template(
        self,
        template_id: str,
        name: str,
        docker_image: str,
        docker_image_digest: str,
        docker_image_tag: str = "latest",
        ports: Optional[List[int]] = None,
        start_command: Optional[str] = None,
        **kwargs
    ) -> Template:
        """Update existing template."""
        templates = self._request("GET", "/templates").json()
        current = next((t for t in templates if t["id"] == template_id), None)

        if not current:
            raise ValueError(f"Template with ID {template_id} not found")

        if current.get("user_id") != self.get_my_user_id():
            raise ValueError(f"Cannot update template {template_id}: not owned by current user")

        payload = current.copy()
        payload.update({
                "name": name,
                "docker_image": docker_image,
                "docker_image_digest": docker_image_digest,
                "docker_image_tag": docker_image_tag,
                "internal_ports": ports or [22, 8000],
                "startup_commands": start_command or "",
                "category": kwargs.get("category", payload.get("category", "UBUNTU")),
            "container_start_immediately": kwargs.get("container_start_immediately", payload.get("container_start_immediately", True)),
                "description": kwargs.get("description", payload.get("description", name)),
                "entrypoint": kwargs.get("entrypoint", payload.get("entrypoint", "")),
                "environment": kwargs.get("environment", payload.get("environment", {})),
                "is_private": kwargs.get("is_private", payload.get("is_private", False)),
                "readme": kwargs.get("readme", payload.get("readme", name)),
                "volumes": kwargs.get("volumes", payload.get("volumes", [])),
        })

        resp = self._request("PUT", f"/templates/{template_id}", json=payload).json()
        return Template(
            id=template_id,
            huid=generate_huid(template_id),
            name=payload['name'],
            docker_image=payload['docker_image'],
            docker_image_tag=payload['docker_image_tag'],
            category=payload['category'],
            status=resp.get("status", "unknown"),
        )

    def upsert_template(
        self,
        name: str,
        docker_image: str,
        docker_image_digest: str,
        docker_image_tag: str = "latest",
        ports: Optional[List[int]] = None,
        start_command: Optional[str] = None,
        **kwargs
    ) -> Template:
        """Create template or update existing if name matches."""
        my_templates = self.templates(only_my=True)
        existing = next((t for t in my_templates if t.name == name), None)

        if existing:
            return self.update_template(
                template_id=existing.id,
                name=name,
                docker_image=docker_image,
                docker_image_digest=docker_image_digest,
                docker_image_tag=docker_image_tag,
                ports=ports,
                start_command=start_command,
                **kwargs
            )
        else:
            return self.create_template(
                name=name,
                docker_image=docker_image,
                docker_image_digest=docker_image_digest,
                docker_image_tag=docker_image_tag,
                ports=ports,
                start_command=start_command,
                **kwargs,
            )

    def wallets(self) -> List[Dict[str, Any]]:
        """Get user's funding wallets."""
        user = self._request("GET", "/users/me").json()
        resp = self._request(
            "GET",
            f"/wallet/available-wallets/{user['stripe_customer_id']}",
            base_url=self.config.base_pay_url,
            headers={"X-Api-Key": "admin-test-key"},
        )
        return resp.json()

    def add_wallet(self, bt_wallet: Any) -> None:
        """Link Bittensor wallet with user account."""
        pay_headers = {"X-Api-Key": "admin-test-key"}
        access_key = self._request(
            "GET", "/token/generate", base_url=self.config.base_pay_url, headers=pay_headers
        ).json()["access_key"]
        sig = bt_wallet.coldkey.sign(access_key.encode()).hex()
        user = self._request("GET", "/users/me").json()
        response = self._request("POST", "/tao/create-transfer", json={"amount": 10})
        app_id = response.json()["url"].split("app_id=")[1].split("&")[0]

        self._request(
            "POST",
            "/token/verify",
            base_url=self.config.base_pay_url,
            headers=pay_headers,
            json={
                "coldkey_address": bt_wallet.coldkeypub.ss58_address,
                "access_key": access_key,
                "signature": sig,
                "stripe_customer_id": user["stripe_customer_id"],
                "application_id": app_id,
            },
        )

    def balance(self) -> float:
        """Get current user balance."""
        return float(self._request("GET", "/users/me").json().get("balance", 0))


if __name__ == "__main__":
    # Quick demo
    lium = Lium()
    print(f"Executors: {len(lium.ls())}")
    print(f"Pods: {len(lium.ps())}")
    for pod in lium.ps()[:3]:
        print(f"  - {pod.name} ({pod.huid}): {pod.status}")
