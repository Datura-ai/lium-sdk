# Lium SDK

A Python SDK for GPU pod management on the Lium platform.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [License](#license)
- [Changelog](#changelog)
- [Support](#support)

## Installation

```bash
pip install lium-sdk
```

## Usage

```python
from lium_sdk import Lium

# Initialize client (reads API key from LIUM_API_KEY env or ~/.lium/config.ini)
lium = Lium()

# List available executors
executors = lium.ls()
for executor in executors[:5]:
    print(f"{executor.huid}: {executor.gpu_count}x{executor.gpu_type} @ ${executor.price_per_hour}/h")

# Create a pod
executor = executors[0]
pod_info = lium.up(executor_id=executor.id, pod_name="my-pod")

# List active pods
pods = lium.ps()
for pod in pods:
    print(f"{pod.name}: {pod.status}")

# Execute command on pod
result = lium.exec(pod="my-pod", command="nvidia-smi")
print(result["stdout"])

# SSH into pod
ssh_cmd = lium.ssh("my-pod")
print(f"SSH command: {ssh_cmd}")

# Stop pod
lium.down("my-pod")
```

## Development

To set up the development environment, clone the repository and install the dependencies:

```bash
git clone https://github.com/your-username/lium-sdk.git
cd lium-sdk
pip install -e .
```

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Changelog

All notable changes to this project will be documented in the [CHANGELOG.md](CHANGELOG.md) file.

## Support

If you have any issues or questions, please open an issue on GitHub.