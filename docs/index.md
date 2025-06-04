# Celium SDK

## Installation

```bash
pip install celium-sdk
```

## Resource Examples

Below are some examples of how to use the Celium SDK to interact with resources.

### List Pods

```python
import celium

# Ensure you have your API_KEY set as an environment variable or pass it directly
# client = celium.Client(api_key="YOUR_API_KEY")
with celium.Client() as client:
    pods = client.pods.list()
    for pod in pods:
        print(f"Pod ID: {pod.id}, Status: {pod.status}")
```

### Easy Deploy a Pod

```python
import celium

# Ensure you have your API_KEY set as an environment variable or pass it directly
# client = celium.Client(api_key="YOUR_API_KEY")
with celium.Client() as client:
    # Example: Deploy a pod on a machine with 1 NVIDIA RTX A6000 GPU using a specific docker image
    # Replace with your desired machine_query and docker_image or dockerfile/template_id
    try:
        deployed_pod = client.pods.easy_deploy(
            machine_query="1xA6000", 
            docker_image="your_docker_image:latest", # Or use dockerfile="path/to/your/Dockerfile"
                                                  # Or use template_id="your_template_id"
            pod_name="my-first-celium-pod"
        )
        print(f"Successfully deployed pod: {deployed_pod.name} with ID: {deployed_pod.id}")
    except Exception as e:
        print(f"Failed to deploy pod: {e}")

```

### List Pods (Async)

```python
import asyncio
import celium

async def main():
    # Ensure you have your API_KEY set as an environment variable or pass it directly
    # client = celium.AsyncClient(api_key="YOUR_API_KEY")
    async with celium.AsyncClient() as client:
        pods = await client.pods.list()
        for pod in pods:
            print(f"Pod ID: {pod.id}, Status: {pod.status}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Easy Deploy a Pod (Async)

```python
import asyncio
import celium

async def main():
    # Ensure you have your API_KEY set as an environment variable or pass it directly
    # client = celium.AsyncClient(api_key="YOUR_API_KEY")
    async with celium.AsyncClient() as client:
        # Example: Deploy a pod on a machine with 1 NVIDIA RTX A6000 GPU using a specific docker image
        # Replace with your desired machine_query and docker_image or dockerfile/template_id
        try:
            deployed_pod = await client.pods.easy_deploy(
                machine_query="1xA6000", 
                docker_image="your_docker_image:latest", # Or use dockerfile="path/to/your/Dockerfile"
                                                      # Or use template_id="your_template_id"
                pod_name="my-first-async-celium-pod"
            )
            print(f"Successfully deployed pod: {deployed_pod.name} with ID: {deployed_pod.id}")
        except Exception as e:
            print(f"Failed to deploy pod: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### List Available Machines

```python
import celium

# Ensure you have your API_KEY set as an environment variable or pass it directly
# client = celium.Client(api_key="YOUR_API_KEY")
with celium.Client() as client:
    # List all RTX A4000 machines
    machines = client.pods.list_machines(gpu_type="RTX A4000")
    for machine in machines:
        print(f"Machine: {machine.machine_name}, Price: ${machine.price_per_hour}/hour")

    # List machines with 2-4 GPUs, sorted by price
    machines = client.pods.list_machines(
        min_gpu_count=2,
        max_gpu_count=4,
        sort_by="price",
        sort_order="asc"
    )
    for machine in machines:
        print(f"Machine: {machine.machine_name}, GPUs: {machine.specs.gpu.count}, Price: ${machine.price_per_hour}/hour")

    # List machines under $5/hour with at least 1 hour uptime
    machines = client.pods.list_machines(
        max_price_per_hour=5.0,
        min_uptime_minutes=60
    )
    for machine in machines:
        print(f"Machine: {machine.machine_name}, Uptime: {machine.uptime_in_minutes} minutes, Price: ${machine.price_per_hour}/hour")

    # List machines near a specific location (e.g., New York City)
    machines = client.pods.list_machines(
        lat=40.7128,  # New York City latitude
        lon=-74.0060,  # New York City longitude
        max_distance_mile=100  # Within 100 miles
    )
    for machine in machines:
        print(f"Machine: {machine.machine_name}, Location: {machine.executor_ip_address}")
```

### List Available Machines (Async)

```python
import asyncio
import celium

# Ensure you have your API_KEY set as an environment variable or pass it directly
# client = celium.AsyncClient(api_key="YOUR_API_KEY")
async def main():
    async with celium.AsyncClient() as client:
        # List all RTX A4000 machines
        machines = await client.pods.list_machines(gpu_type="RTX A4000")
        for machine in machines:
            print(f"Machine: {machine.machine_name}, Price: ${machine.price_per_hour}/hour")

        # List machines with 2-4 GPUs, sorted by price
        machines = await client.pods.list_machines(
            min_gpu_count=2,
            max_gpu_count=4,
            sort_by="price",
            sort_order="asc"
        )
        for machine in machines:
            print(f"Machine: {machine.machine_name}, GPUs: {machine.specs.gpu.count}, Price: ${machine.price_per_hour}/hour")

        # List machines under $5/hour with at least 1 hour uptime
        machines = await client.pods.list_machines(
            max_price_per_hour=5.0,
            min_uptime_minutes=60
        )
        for machine in machines:
            print(f"Machine: {machine.machine_name}, Uptime: {machine.uptime_in_minutes} minutes, Price: ${machine.price_per_hour}/hour")

        # List machines near a specific location (e.g., New York City)
        machines = await client.pods.list_machines(
            lat=40.7128,  # New York City latitude
            lon=-74.0060,  # New York City longitude
            max_distance_mile=100  # Within 100 miles
        )
        for machine in machines:
            print(f"Machine: {machine.machine_name}, Location: {machine.executor_ip_address}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Available Resources

For a detailed list of available resources and their functionalities, please refer to the following pages:

- [Docker Credentials](./reference/resources/docker-credentials.md)
- [Pods](./reference/resources/pods.md)
- [SSH Keys](./reference/resources/ssh-keys.md)
- [Templates](./reference/resources/templates.md)