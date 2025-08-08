"""
Lium SDK - Clean, Unix-style SDK for GPU pod management
~400 lines of elegant Python instead of 1000+ lines of boilerplate
"""
import os
import time
import hashlib
import random
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional, List, Dict, Union
from contextlib import contextmanager
from functools import wraps
import paramiko
import requests
from dotenv import load_dotenv

load_dotenv()


class LiumAPIError(Exception):
    """Base exception for API errors"""

    def __init__(self, message: str, response_data: dict | None = None):
        super().__init__(message)
        self.response_data = response_data


class LiumAuthenticationError(LiumAPIError):
    """API key authentication failed (401)"""

    pass


class LiumRateLimitError(LiumAPIError):
    """Rate limit exceeded (429)"""

    pass


class LiumServerError(LiumAPIError):
    """Server error (5xx)"""

    pass


class LiumValidationError(LiumAPIError):
    """Request validation error (400, 422)"""

    pass


# models.py
@dataclass
class PodInfo:
    """Information about a pod."""

    id: str
    name: str
    status: str
    huid: str
    ssh_cmd: str | None
    ports: dict[str, int]
    created_at: str
    updated_at: str
    executor: dict[str, Any]
    template: dict[str, Any]


@dataclass
class ExecutorInfo:
    """Information about an executor."""

    id: str
    huid: str
    machine_name: str
    gpu_type: str
    gpu_count: int
    price_per_hour: float
    price_per_gpu_hour: float
    location: dict[str, str]
    specs: dict[str, Any]
    status: str


# helpers.py
def get_config_value(param: str) -> str | None:
    """Get configuration value from ~/.lium/config.ini file."""
    config_path = Path.home() / ".lium" / "config.ini"

    if not config_path.exists():
        return None

    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        # Parse parameter like "api.api_key" -> section "api", key "api_key"
        if "." in param:
            section, key = param.split(".", 1)
            return config.get(section, key, fallback=None)
        else:
            # If no section specified, try 'default' section
            return config.get("default", param, fallback=None)
    except (configparser.Error, OSError):
        return None


ADJECTIVES = [
    "swift",
    "silent",
    "brave",
    "bright",
    "calm",
    "clever",
    "eager",
    "fierce",
    "gentle",
    "grand",
    "happy",
    "jolly",
    "kind",
    "lively",
    "merry",
    "noble",
    "proud",
    "silly",
    "witty",
    "zesty",
    "cosmic",
    "digital",
    "electric",
    "frozen",
    "golden",
    "hydro",
    "iron",
    "laser",
    "lunar",
    "solar",
]  # 30 adjectives

NOUNS = [
    "hawk",
    "lion",
    "tiger",
    "eagle",
    "fox",
    "wolf",
    "shark",
    "viper",
    "cobra",
    "falcon",
    "jaguar",
    "leopard",
    "lynx",
    "panther",
    "puma",
    "cougar",
    "condor",
    "raven",
    "photon",
    "quasar",
    "vector",
    "matrix",
    "cipher",
    "pixel",
    "comet",
    "nebula",
    "nova",
    "orbit",
    "axiom",
    "sphinx",
]  # 30 nouns


def generate_human_id(executor_id: str) -> str:
    """Generates a deterministic human-readable ID from the executor_id."""
    if not executor_id or not isinstance(executor_id, str):
        return "invalid-id-huid"

    # Use MD5 hash of the executor_id for deterministic choices
    hasher = hashlib.md5(executor_id.encode("utf-8"))
    digest = hasher.hexdigest()

    # Use parts of the hash to select words and suffix
    # Ensure indices are within bounds of the word lists
    adj_idx = int(digest[0:4], 16) % len(ADJECTIVES)
    noun_idx = int(digest[4:8], 16) % len(NOUNS)

    # Use last 2 characters of the hash for the numeric suffix for consistency
    suffix_chars = digest[-2:]

    adjective = ADJECTIVES[adj_idx]
    noun = NOUNS[noun_idx]

    return f"{adjective}-{noun}-{suffix_chars}"


def extract_gpu_model(machine_name: str) -> str:
    """Extract just the model number from GPU name."""
    # Pattern to match various GPU models - ORDER MATTERS!
    patterns = [
        (r"RTX\s*(\d{4}[A-Z]?)", "RTX"),  # RTX 4090, RTX 3090, RTX 4090 D
        (r"RTX\s*A(\d{4})", "A"),  # RTX A5000, RTX A6000
        (r"H(\d{2,3})", "H"),  # H100, H200 - BEFORE A pattern
        (r"B(\d{2,3})", "B"),  # B200
        (r"L(\d{2}[S]?)", "L"),  # L40, L40S
        (r"A(\d{2,3})", "A"),  # A100, A40 - AFTER H pattern
    ]

    for pattern, prefix in patterns:
        match = re.search(pattern, machine_name, re.IGNORECASE)
        if match:
            # Get the matched number/model
            model = match.group(1)
            # Add the letter prefix back for non-RTX cards
            if prefix == "RTX":
                return model
            else:
                return f"{prefix}{model}"

    # If no pattern matches, return a shortened version
    return machine_name.split()[-1] if machine_name else "Unknown"


def get_ssh_public_keys() -> list[str]:
    """Reads SSH public key(s) with intelligent fallback.

    Returns:
        A list of public key strings, or an empty list if not found or error.
    """
    # Try config first
    public_key_path_str = get_config_value("ssh.key_path")
    
    # If no config, try common locations
    if not public_key_path_str:
        for key_name in ["id_ed25519.pub", "id_rsa.pub", "id_ecdsa.pub"]:
            possible_path = Path.home() / ".ssh" / key_name
            if possible_path.exists():
                public_key_path_str = str(possible_path)
                break
    
    if not public_key_path_str:
        return []

    resolved_public_key_path = Path(public_key_path_str).expanduser()
    
    # Handle both .pub and non-.pub paths
    if resolved_public_key_path.suffix != ".pub":
        resolved_public_key_path = resolved_public_key_path.with_suffix(".pub")

    if not resolved_public_key_path.exists():
        logger.warning(f"Public key file not found at {resolved_public_key_path}")
        return []

    # Read keys using list comprehension
    try:
        with open(resolved_public_key_path) as f:
            public_keys = [
                line.strip() 
                for line in f 
                if line.strip() and (line.startswith("ssh-") or line.startswith("ecdsa-"))
            ]
        if not public_keys:
            logger.warning(f"No valid public keys found in {resolved_public_key_path}")
        return public_keys
    except (OSError, IOError):
        logger.exception(f"Error reading public key file {resolved_public_key_path}")
        return []


class Lium:
    """
    Lium SDK for managing Celium Compute GPU pods.

    API Key Configuration:
        The SDK will look for the API key in the following order:
        1. Constructor parameter: Lium(api_key="your-key")
        2. Environment variable: LIUM_API_KEY
        3. .env file: LIUM_API_KEY=your-key
        4. Config file: ~/.lium/config.ini

    Example usage:
        # Initialize
        from lium import Lium
        lium = Lium(api_key="your-api-key")

        # List available pods
        all_pods = lium.ls()
        h100s = lium.ls(gpu_type="H100")

        # Start pods
        pod = lium.up(executor_id="executor-uuid", pod_name="my-pod")

        # List active pods
        my_pods = lium.ps()

        # Execute commands - accepts pod ID, name, HUID, or PodInfo object
        result = lium.exec(pod, command="nvidia-smi")
        result = lium.exec("my-pod", command="nvidia-smi")
        result = lium.exec("pod-uuid", command="nvidia-smi")

        # Transfer files - accepts pod ID, name, HUID, or PodInfo object
        lium.scp("my-pod", local_path="./file.txt", remote_path="/home/file.txt")

        # Stop pods - accepts pod ID, name, HUID, or PodInfo object
        lium.down("my-pod")
    """

    def __init__(self, api_key: str | None = None, base_url: str = "https://lium.io/api"):
        """
        Initialize Lium SDK.

        Args:
            api_key: API key for authentication. If None, will try to get from environment or config.
            base_url: Base URL for the API
        """
        self.api_key = api_key or self._get_api_key()
        self.base_url = base_url
        self.headers = {"X-API-KEY": self.api_key}
        self._ssh_key_path = None

        if not self.api_key:
            raise ValueError(
                "API key is required. Provide it via:\n"
                "1. Constructor: Lium(api_key='...')\n"
                "2. Environment: export LIUM_API_KEY='...'\n"
                "3. .env file: LIUM_API_KEY=...\n"
                "4. Config file: ~/.lium/config.ini [api] api_key=..."
            )

    @staticmethod
    def _get_api_key() -> str | None:
        """Get API key from environment or config file."""
        # Load .env file if it exists
        load_dotenv()

        # 1. Environment variable (including from .env file)
        api_key = os.getenv("LIUM_API_KEY")
        if api_key:
            return api_key

        # 2. Config file
        return get_config_value("api.api_key")

    @staticmethod
    def _generate_huid(executor_id: str) -> str:
        """Generate human-readable ID from executor ID."""
        # Import locally to avoid circular dependencies
        return generate_human_id(executor_id)

    @staticmethod
    def _extract_gpu_type(machine_name: str) -> str:
        """Extract GPU model from machine name."""
        # Import locally to avoid circular dependencies
        return extract_gpu_model(machine_name)

    def _resolve_pod(self, pod: str | PodInfo) -> PodInfo:
        """
        Resolve pod identifier to PodInfo object.

        Args:
            pod: Pod ID, name, HUID, or PodInfo object

        Returns:
            PodInfo object

        Raises:
            ValueError: If pod not found
        """
        if isinstance(pod, PodInfo):
            return pod

        # It's a string identifier - search by ID, name, or HUID
        pods = self.ps()
        found_pod = next((p for p in pods if p.id == pod or p.name == pod or p.huid == pod), None)

        if not found_pod:
            raise ValueError(f"Pod '{pod}' not found")

        return found_pod

    def _make_request(self, method: str, endpoint: str, timeout: int = 30, **kwargs) -> requests.Response:
        """Make HTTP request to API with retry and proper error handling."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Retry configuration
        max_retries = 6
        base_delay = 1.0
        retryable_errors = (LiumRateLimitError, LiumServerError, requests.exceptions.RequestException)

        for attempt in range(max_retries):
            try:
                response = requests.request(method, url, headers=self.headers, timeout=timeout, **kwargs)

                # Handle response status
                if response.ok:
                    return response

                # Parse error data
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", f"HTTP {response.status_code}")
                except (ValueError, requests.exceptions.JSONDecodeError):
                    error_data = None
                    error_msg = f"HTTP {response.status_code}"

                # Map status codes to exceptions
                status_errors = {
                    401: (LiumAuthenticationError, "Authentication failed"),
                    400: (LiumValidationError, "Invalid request"),
                    422: (LiumValidationError, "Validation error"),
                    429: (LiumRateLimitError, "Rate limit exceeded"),
                }

                # Raise appropriate exception
                if response.status_code in status_errors:
                    exc_class, default_msg = status_errors[response.status_code]
                    raise exc_class(error_msg or default_msg, error_data)
                elif 500 <= response.status_code < 600:
                    raise LiumServerError(f"Server error: {response.status_code}", error_data)
                else:
                    raise LiumAPIError(f"Unexpected API error: {response.status_code}", error_data)

            except retryable_errors as e:
                # Check if we should retry
                if attempt == max_retries - 1:
                    if isinstance(e, requests.exceptions.RequestException):
                        raise LiumAPIError(f"Connection error: {e!s}") from e
                    raise

                # Calculate delay with exponential backoff and jitter
                delay = base_delay * (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Request failed ({e.__class__.__name__}), "
                    f"retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)

            except Exception:
                # Non-retryable errors - re-raise immediately
                raise

        raise LiumAPIError("Request failed after all retries")

    # Core API Methods

    def ls(self, gpu_type: str | None = None) -> list[ExecutorInfo]:
        """
        List available executors.

        Args:
            gpu_type: Filter by GPU type (e.g., "H100", "4090")

        Returns:
            List of ExecutorInfo objects
        """
        response = self._make_request("GET", "/executors")
        executors_data = response.json()

        # Use list comprehension with helper function for transformation
        executors = [
            self._transform_executor(exec_data)
            for exec_data in executors_data
        ]

        # Filter by GPU type if specified
        if gpu_type:
            executors = [e for e in executors if e.gpu_type.upper() == gpu_type.upper()]

        return executors
    
    def _transform_executor(self, data: dict) -> ExecutorInfo:
        """Transform API executor data to ExecutorInfo object."""
        gpu_count = data.get("specs", {}).get("gpu", {}).get("count", 1)
        machine_name = data.get("machine_name", "")
        
        return ExecutorInfo(
            id=data.get("id", ""),
            huid=self._generate_huid(data.get("id", "")),
            machine_name=machine_name,
            gpu_type=self._extract_gpu_type(machine_name),
            gpu_count=gpu_count,
            price_per_hour=data.get("price_per_hour", 0),
            price_per_gpu_hour=data.get("price_per_hour", 0) / gpu_count if gpu_count > 0 else 0,
            location=data.get("location", {}),
            specs=data.get("specs", {}),
            status=data.get("status", "unknown")
        )

    def ps(self) -> list[PodInfo]:
        """
        List active pods.

        Returns:
            List of PodInfo objects
        """
        response = self._make_request("GET", "/pods")
        pods_data = response.json()

        # Use list comprehension for cleaner code
        return [
            PodInfo(
                id=pod_data.get("id", ""),
                name=pod_data.get("pod_name", ""),
                status=pod_data.get("status", "unknown"),
                huid=self._generate_huid(pod_data.get("id", "")),
                ssh_cmd=pod_data.get("ssh_connect_cmd"),
                ports=pod_data.get("ports_mapping", {}),
                created_at=pod_data.get("created_at", ""),
                updated_at=pod_data.get("updated_at", ""),
                executor=pod_data.get("executor", {}),
                template=pod_data.get("template", {})
            )
            for pod_data in pods_data
        ]

    def get_templates(self) -> list[dict[str, Any]]:
        """
        Get available templates.

        Returns:
            List of template dictionaries
        """
        response = self._make_request("GET", "/templates")
        return response.json()

    def up(
        self,
        executor_id: str,
        pod_name: str = None,
        template_id: str | None = None,
        ssh_public_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Start a new pod on an executor.

        Args:
            executor_id: UUID of the executor
            pod_name: Name for the pod
            template_id: UUID of template to use. If None, uses first available template.
            ssh_public_keys: List of SSH public keys. If None, tries to load from config.

        Returns:
            Pod information dictionary
        """
        if not template_id:
            templates = self.get_templates()
            if not templates:
                raise ValueError("No templates available")
            template_id = templates[0]["id"]

        if not ssh_public_keys:
            ssh_public_keys = self._get_ssh_public_keys()

        if not ssh_public_keys:
            raise ValueError("No SSH public keys found. Configure ssh.key_path or provide ssh_public_keys parameter.")

        payload = {"pod_name": pod_name, "template_id": template_id, "user_public_key": ssh_public_keys}

        # Get initial pod list to compare after creation
        initial_pods = {p.name: p.id for p in self.ps()}

        response = self._make_request("POST", f"/executors/{executor_id}/rent", json=payload)
        api_response = response.json()

        # If API response contains pod info, return it
        if api_response and "id" in api_response:
            return api_response

        # Otherwise, find the newly created pod by comparing pod lists
        # Wait a moment for the pod to appear
        time.sleep(2)

        current_pods = self.ps()
        for pod in current_pods:
            if pod.name == pod_name and pod.name not in initial_pods:
                return {
                    "id": pod.id,
                    "name": pod.name,
                    "status": pod.status,
                    "huid": pod.huid,
                    "ssh_cmd": pod.ssh_cmd,
                    "executor_id": executor_id,
                }

        # If we still can't find it, return what we have
        return api_response or {"name": pod_name, "executor_id": executor_id}

    def down(self, pod: str | PodInfo | None = None, executor_id: str | None = None) -> dict[str, Any]:
        """
        Stop a pod.

        Args:
            pod: Pod ID, name, HUID, or PodInfo object to stop
            executor_id: Executor ID (if pod not provided)

        Returns:
            API response
        """
        if pod:
            pod_info = self._resolve_pod(pod)
            executor_id = pod_info.executor.get("id")

        if not executor_id:
            raise ValueError("Either pod or executor_id must be provided")

        response = self._make_request("DELETE", f"/executors/{executor_id}/rent")
        return response.json()

    def rm(self, pod: str | PodInfo | None = None, executor_id: str | None = None) -> dict[str, Any]:
        """
        stop a pod. same as down
        """
        return self.down(pod, executor_id)

    # SSH and Execution Methods

    def _get_ssh_private_key_path(self) -> Path | None:
        """Get SSH private key path from config."""
        if self._ssh_key_path:
            return self._ssh_key_path

        # Import locally to avoid circular dependencies

        key_path = get_config_value("ssh.key_path")
        if key_path:
            # Remove .pub extension if present
            key_path = key_path.rstrip(".pub")
            self._ssh_key_path = Path(key_path).expanduser()
            return self._ssh_key_path

        # Try common SSH key locations
        for key_name in ["id_rsa", "id_ed25519", "id_ecdsa"]:
            key_path = Path.home() / ".ssh" / key_name
            if key_path.exists():
                self._ssh_key_path = key_path
                return self._ssh_key_path

        return None

    @staticmethod
    def _get_ssh_public_keys() -> list[str]:
        """Get SSH public keys from config."""
        return get_ssh_public_keys()

    def _get_ssh_connection_info(self, pod: str | PodInfo) -> tuple[str, str, int]:
        """Get SSH connection info for a pod."""
        pod_info = self._resolve_pod(pod)

        if not pod_info.ssh_cmd:
            raise ValueError(f"Pod {pod_info.name} has no SSH connection available")

        # Parse SSH command: "ssh user@host -p port"
        import shlex

        parts = shlex.split(pod_info.ssh_cmd)
        user_host = parts[1]
        user, host = user_host.split("@")

        port = 22
        if "-p" in parts:
            port_index = parts.index("-p") + 1
            if port_index < len(parts):
                port = int(parts[port_index])

        return user, host, port

    @staticmethod
    def _load_ssh_key(private_key_path: Path) -> paramiko.PKey:
        """Load SSH private key trying different key types."""
        for key_type in [paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey]:
            try:
                return key_type.from_private_key_file(str(private_key_path))
            except paramiko.ssh_exception.SSHException:
                logger.debug(f"Failed to load {key_type.__name__} from {private_key_path}. Trying next type.")
                continue
        raise ValueError("Could not load SSH private key")

    @contextmanager
    def ssh_connection(self, pod: str | PodInfo, timeout: int = 30):
        """
        Context manager for SSH connections.
        
        Usage:
            with lium.ssh_connection(pod) as client:
                stdin, stdout, stderr = client.exec_command("ls")
        """
        ssh_client = self._prepare_ssh_client(pod, timeout)
        try:
            yield ssh_client
        finally:
            ssh_client.close()
    
    def _prepare_ssh_client(self, pod: str | PodInfo, timeout: int = 30) -> paramiko.SSHClient:
        """
        Prepare and connect SSH client.

        Args:
            pod: Pod ID, name, HUID, or PodInfo object
            timeout: SSH connection timeout

        Returns:
            Connected SSH client

        Raises:
            ValueError: If SSH key not found or cannot be loaded
        """
        # Get SSH key path
        private_key_path = self._get_ssh_private_key_path()
        if not private_key_path or not private_key_path.exists():
            raise ValueError("SSH private key not found. Configure ssh.key_path in ~/.lium/config.ini")

        # Load key and get connection info
        loaded_key = self._load_ssh_key(private_key_path)
        user, host, port = self._get_ssh_connection_info(pod)

        # Connect
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=host, port=port, username=user, pkey=loaded_key, timeout=timeout)

        return ssh_client

    @staticmethod
    def _prepare_command(command: str, env_vars: dict[str, str] | None = None) -> str:
        """
        Add environment variables to command if needed.

        Args:
            command: Base command to execute
            env_vars: Optional environment variables to set

        Returns:
            Command with environment variables prepended if any
        """
        if env_vars:
            env_exports = " && ".join([f'export {k}="{v}"' for k, v in env_vars.items()])
            return f"{env_exports} && {command}"
        return command

    def exec(
        self, pod: str | PodInfo, command: str, env_vars: dict[str, str] | None = None, timeout: int = 30
    ) -> dict[str, Any]:
        """
        Execute a command on a pod via SSH.

        Args:
            pod: Pod ID, name, HUID, or PodInfo object
            command: Command to execute
            env_vars: Environment variables to set
            timeout: SSH connection timeout

        Returns:
            Dictionary with stdout, stderr, exit_code, and success fields
        """
        command = self._prepare_command(command, env_vars)
        
        with self.ssh_connection(pod, timeout) as ssh_client:
            stdin, stdout, stderr = ssh_client.exec_command(command)
            
            stdout_text = stdout.read().decode("utf-8", errors="replace")
            stderr_text = stderr.read().decode("utf-8", errors="replace")
            exit_code = stdout.channel.recv_exit_status()
            
            return {"stdout": stdout_text, "stderr": stderr_text, "exit_code": exit_code, "success": exit_code == 0}

    def stream_exec(
        self, pod: str | PodInfo, command: str, env_vars: dict[str, str] | None = None, timeout: int = 30
    ) -> Generator[dict[str, str], None, None]:
        """
        Execute a command on a pod via SSH with streaming output.

        Args:
            pod: Pod ID, name, HUID, or PodInfo object
            command: Command to execute
            env_vars: Environment variables to set
            timeout: SSH connection timeout

        Yields:
            Dictionary with "type" ("stdout" or "stderr") and "data" (string chunk)
        """
        command = self._prepare_command(command, env_vars)
        
        with self.ssh_connection(pod, timeout) as ssh_client:
            stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True)
            stdin.close()

            channel = stdout.channel
            channel.settimeout(0.1)  # Non-blocking with small timeout

            while not channel.closed or channel.recv_ready() or channel.recv_stderr_ready():
                # Read stdout
                if channel.recv_ready():
                    data = channel.recv(4096).decode("utf-8", errors="replace")
                    if data:
                        yield {"type": "stdout", "data": data}

                # Read stderr
                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                    if data:
                        yield {"type": "stderr", "data": data}

    def _exec_single_pod_safe(
        self, pod: str | PodInfo, command: str, env_vars: dict[str, str] | None = None, timeout: int = 30
    ) -> dict[str, Any]:
        """
        Execute command on a single pod with error handling.

        Args:
            pod: Pod ID, name, HUID, or PodInfo object
            command: Command to execute
            env_vars: Environment variables to set
            timeout: SSH connection timeout

        Returns:
            Dictionary with result including pod info and success flag
        """
        try:
            exec_result = self.exec(pod, command, env_vars, timeout)
        except Exception as e:
            return {
                "pod": pod.id if isinstance(pod, PodInfo) else pod,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False,
            }
        else:
            exec_result["pod"] = pod.id if isinstance(pod, PodInfo) else pod
            return exec_result

    def exec_all(
        self,
        pods: list[str | PodInfo],
        command: str,
        env_vars: dict[str, str] | None = None,
        timeout: int = 30,
        max_workers: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute command on multiple pods in parallel.

        Args:
            pods: List of pod identifiers (ID, name, HUID, or PodInfo objects)
            command: Command to execute
            env_vars: Environment variables to set
            timeout: SSH connection timeout
            max_workers: Maximum number of concurrent threads (default: min(32, len(pods)))

        Returns:
            List of execution results in the same order as input pods
        """
        if not pods:
            return []

        if max_workers is None:
            max_workers = min(32, len(pods))

        with ThreadPoolExecutor(max_workers=max_workers) as executor_pool:
            # Submit all tasks
            futures = []
            for pod in pods:
                future = executor_pool.submit(self._exec_single_pod_safe, pod, command, env_vars, timeout)
                futures.append(future)

            # Collect results in order
            result_list = []
            for future in futures:
                result_list.append(future.result())

        return result_list

    def scp(self, pod: str | PodInfo, local_path: str, remote_path: str, timeout: int = 30) -> None:
        """
        Upload a file to a pod via SFTP.

        Args:
            pod: Pod ID, name, HUID, or PodInfo object
            local_path: Local file path
            remote_path: Remote file path
            timeout: Connection timeout
        """
        pass

    #     private_key_path = self._get_ssh_private_key_path()
    #     if not private_key_path or not private_key_path.exists():
    #         raise ValueError("SSH private key not found")
    #
    #     user, host, port = self._get_ssh_connection_info(pod)
    #
    #     ssh_client = paramiko.SSHClient()
    #     ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #
    #     try:
    #         # Load SSH key
    #         key_types = [paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey, paramiko.DSSKey]
    #         loaded_key = None
    #
    #         for key_type in key_types:
    #             try:
    #                 loaded_key = key_type.from_private_key_file(str(private_key_path))
    #                 break
    #             except paramiko.ssh_exception.SSHException:
    #                 continue
    #
    #         if not loaded_key:
    #             raise ValueError("Could not load SSH private key")
    #
    #         ssh_client.connect(hostname=host, port=port, username=user, pkey=loaded_key, timeout=timeout)
    #         sftp = ssh_client.open_sftp()
    #         sftp.put(local_path, remote_path)
    #         sftp.close()
    #
    #     finally:
    #         ssh_client.close()
    #

    def rsync(
        self,
        pod: str | PodInfo,
        local_path: str,
        remote_path: str,
        direction: str = "up",
        delete: bool = False,
        exclude: list[str] | None = None,
    ) -> bool:
        """
        Sync directories using rsync.

        Args:
            pod: Pod ID, name, HUID, or PodInfo object
            local_path: Local directory path
            remote_path: Remote directory path
            direction: "up" (local to remote) or "down" (remote to local)
            delete: Delete extraneous files
            exclude: List of patterns to exclude

        Returns:
            True if successful
        """
        pass
        # private_key_path = self._get_ssh_private_key_path()
        # if not private_key_path or not private_key_path.exists():
        #     raise ValueError("SSH private key not found")
        #
        # user, host, port = self._get_ssh_connection_info(pod)
        #
        # # Build rsync command
        # rsync_cmd = [
        #     "rsync", "-avz",
        #     "-e", f"ssh -i {private_key_path} -p {port} -o StrictHostKeyChecking=no"
        # ]
        #
        # if delete:
        #     rsync_cmd.append("--delete")
        #
        # if exclude:
        #     for pattern in exclude:
        #         rsync_cmd.extend(["--exclude", pattern])
        #
        # if direction == "up":
        #     rsync_cmd.extend([local_path, f"{user}@{host}:{remote_path}"])
        # else:
        #     rsync_cmd.extend([f"{user}@{host}:{remote_path}", local_path])
        #
        # try:
        #     result = subprocess.run(rsync_cmd, capture_output=True, text=True, check=True)
        #     return True
        # except subprocess.CalledProcessError as e:
        #     raise RuntimeError(f"Rsync failed: {e.stderr}")

    # Utility Methods

    def wait_for_pod_ready(self, pod: str | PodInfo, max_wait: int = 300, check_interval: int = 10) -> bool:
        """
        Wait for a pod to be ready.

        Args:
            pod: Pod ID, name, HUID, or PodInfo object
            max_wait: Maximum wait time in seconds
            check_interval: Check interval in seconds

        Returns:
            True if pod is ready, False if timeout
        """
        pod_info = self._resolve_pod(pod)
        start_time = time.time()

        while time.time() - start_time < max_wait:
            pods = self.ps()
            current_pod = next((p for p in pods if p.id == pod_info.id), None)

            if current_pod and current_pod.status.upper() == "RUNNING" and current_pod.ssh_cmd:
                return True

            time.sleep(check_interval)

        return False

    def get_pod_by_name(self, name: str) -> PodInfo | None:
        """Get pod by name or HUID."""
        pods = self.ps()
        return next((p for p in pods if p.name == name or p.huid == name), None)

    def get_executor_by_huid(self, huid: str) -> ExecutorInfo | None:
        """Get executor by HUID."""
        executors = self.ls()
        return next((e for e in executors if e.huid == huid), None)


# Convenience functions


def init(api_key: str | None = None) -> Lium:
    """Create a Lium SDK client."""
    return Lium(api_key=api_key)


def list_gpu_types(api_key: str | None = None) -> list[str]:
    """Get list of available GPU types."""
    client = Lium(api_key=api_key)
    executors = client.ls()
    return list(set(e.gpu_type for e in executors))


if __name__ == "__main__":
    # Demo script
    print("=== Lium SDK Demo ===")
    lium = Lium()

    # 1. List executors
    print("1. Finding L40S executors...")
    executors = lium.ls("L40S")
    if not executors:
        print("No L40S executors available")
        exit(1)
    executor = executors[0]
    executor2 = executors[1]
    print(f"   Using: {executor.machine_name} ({executor.huid})")

    # 2. Get template
    print("2. Getting templates...")
    templates = lium.get_templates()
    template = next((t for t in templates if t["name"].lower() == "dind"), None)
    if not template:
        print("No DIND template found")
        exit(1)
    print(f"   Using: {template['name']}")

    # 3. Create 2 pods
    print("3. Creating 2 pods...")
    pod1 = lium.up(executor.id, "demo-pod-1", template["id"])
    pod2 = lium.up(executor2.id, "demo-pod-2", template["id"])
    print(f"   Created: {pod1.get('name', 'pod1')} and {pod2.get('name', 'pod2')}")

    # 4. Wait for ready
    print("4. Waiting for pods to be ready...")
    lium.wait_for_pod_ready(pod1["id"])
    lium.wait_for_pod_ready(pod2["id"])
    print("   Both pods ready!")

    # 5. Show ready pods
    print("5. Listing active pods...")
    pods = lium.ps()
    for pod in pods:
        print(f"   {pod.name} ({pod.huid}) - {pod.status}")

    # 6. Single exec
    print("6. Single exec test...")
    result = lium.exec(pods[0], "echo 'Hello from single exec'")
    print(f"   Result: {result['stdout'].strip()}")

    # 7. Stream exec
    print("7. Stream exec test...")
    for chunk in lium.stream_exec(pods[0], 'for i in {1..3}; do echo "Count $i"; sleep 1; done'):
        print(f"   [{chunk['type']}] {chunk['data']}", end="")

    # 8. Batch exec
    print("8. Batch exec test... (curl ifconfig.me)")
    results = lium.exec_all(pods, "curl ifconfig.me")
    for result in results:
        status = "✓" if result["success"] else "✗"
        print(f"   {status} {result['pod']}: {result['stdout'].strip()}")

    # 9. Delete all
    print("9. Cleaning up...")
    for pod in pods:
        lium.rm(pod)
    print("   All pods deleted")

    # 10. Verify cleanup
    print("10. Verifying cleanup...")
    final_pods = lium.ps()
    print(f"    Active pods: {len(final_pods)}")

    print("=== Demo Complete ===")
