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

## Available Resources

For a detailed list of available resources and their functionalities, please refer to the following pages:

- [Docker Credentials](./reference/resources/docker-credentials.md)
- [Pods](./reference/resources/pods.md)
- [SSH Keys](./reference/resources/ssh-keys.md)
- [Templates](./reference/resources/templates.md)