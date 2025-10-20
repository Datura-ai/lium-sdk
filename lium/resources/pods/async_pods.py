import uuid
import time
from typing import Any
from lium.models.pod import Pod, PodList
from lium.resources.base import BaseAsyncResource
from lium.resources.pods.pods_core import _PodsCore
from lium.models.executor import Executor, ExecutorFilterQuery
from lium.utils.logging import logger


class AsyncPods(BaseAsyncResource, _PodsCore):
    """
    Async pods resource.
    """
    
    async def list_executors(self, filter_query: ExecutorFilterQuery | dict | None = None) -> list[Executor]:
        """
        List all executors. These are the machines from subnet that aren't being rented out.

        :param filter_query: Filter query to filter the executors.
        :type filter_query: ExecutorFilterQuery or dict or None
        :return: List of executors.
        :rtype: list[Executor]
        """
        args, kwargs = self._list_executors_params(filter_query)
        resp = await self._t.arequest(*args, **kwargs)
        return self._parse_list_executors_response(resp.json())

    async def create(
        self, 
        id_in_site: uuid.UUID, 
        pod_name: str, 
        template_id: uuid.UUID, 
        user_public_key: list[str],
    ) -> Pod:
        """
        Create a pod.

        :param id_in_site: The id of the pod in the site.
        :type id_in_site: uuid.UUID
        :param pod_name: The name of the pod.
        :type pod_name: str
        :param template_id: The id of the template to deploy.
        :type template_id: uuid.UUID
        :param user_public_key: The user public key to use for the pod.
        :type user_public_key: list[str]
        :return: The created pod.
        :rtype: Pod
        """
        await self._t.arequest("POST", f"/executors/{id_in_site}/rent", json={
            "pod_name": pod_name,
            "template_id": str(template_id),
            "user_public_key": user_public_key,
        })
        return await self.retrieve(id_in_site)

    async def delete(self, id_in_site: uuid.UUID) -> None:
        """
        Delete a pod.

        :param id_in_site: The id of the pod in the site.
        :type id_in_site: uuid.UUID
        :return: None
        """
        await self._t.arequest("DELETE", f"/executors/{id_in_site}/rent")

    async def list(self) -> list[PodList]:
        """
        List all pods.

        :return: List of pods.
        :rtype: list[PodList]
        """
        resp = await self._t.arequest("GET", "/pods")
        return self._parse_list_pods_response(resp.json())
    
    async def retrieve(self, id: uuid.UUID, wait_until_running: bool = False, timeout: int = 5 * 60) -> Pod:
        """
        Retrieve a pod.

        :param id: The id of the pod.
        :type id: uuid.UUID
        :param wait_until_running: Whether to wait until the pod is running.
        :type wait_until_running: bool, optional
        :param timeout: Timeout in seconds to wait for the pod to be running.
        :type timeout: int, optional
        :return: The retrieved pod.
        :rtype: Pod
        """
        resp = await self._t.arequest("GET", f"/pods/{id}")
        elapsed_time = 0
        pod = None
        while elapsed_time < timeout:
            resp = await self._t.arequest("GET", f"/pods/{id}")
            pod = self._parse_pod_response(resp.json())
            if not wait_until_running or pod.status == "RUNNING":
                return pod
            time.sleep(5)
            elapsed_time += 5
            logger.debug(f"Pod {id} status: {pod.status}, elapsed time: {elapsed_time}s")
        return pod
    
    async def easy_deploy(
        self,
        machine_query: str,
        docker_image: str | None = None,
        dockerfile: str | None = None,
        template_id: str | None = None,
        additional_machine_filter: dict[str, Any] = {},
        pod_name: str | None = None,
    ) -> None:
        """Easy deploy a pod. 

        :param machine_query: The machine query to filter the executors. Find executors with machine name and count. 
        E.g. `1XA6000` will find a machine with 1 X NVIDIA RTX A6000. Count of GPUs can be skipped like `H200`
        If you want to filter multiple machines, you can use `H200,A6000` or `H200,A6000,A100`
        :type machine_query: str
        :param docker_image: The docker image to deploy. Needs to be full image name with tag. 
        If either docker_image or dockerfile is provided, sdk will create a custom template for the pod.
        :type docker_image: str or None
        :param dockerfile: The dockerfile to deploy. If dockerfile is provided, sdk will build a docker image from dockerfile and create 
        one-time template for the pod.
        :type dockerfile: str or None
        :param template_id: The id of the template to deploy. If template_id is provided, docker_image and dockerfile will be ignored.
        Will use provided template from the platform to deploy a pod.
        :type template_id: str or None
        :param additional_machine_filter: Additional machine filter to filter the executors.
        :type additional_machine_filter: dict[str, Any]
        :param pod_name: The name of the pod.
        :type pod_name: str or None
        :return: The created pod.
        :rtype: Pod
        """
        template = None
        is_one_time_template = False
        try:
            # Find matching executor first
            machines, count = self._parse_machine_query(machine_query)
            executors = await self.list_executors(
                {
                    "machine_names": machines,
                    **({"gpu_count_gte": count, "gpu_count_lte": count} if count else {}),
                    **additional_machine_filter
                    }
            )
            if len(executors) == 0:
                logger.warning(f"No executors found for machine query: {machine_query}")
                return
            logger.debug(f"Found {len(executors)} executors for machine query: {machine_query}")
            
            if not template_id:
                # Find the template to deploy 
                is_one_time_template, template = await self._client.templates.create_from_image_or_dockerfile(
                    docker_image, dockerfile
                )   
            else:
                template = await self._client.templates.retrieve(template_id)
            logger.debug(f"Found template: {template.name}({template.id}-{template.docker_image}:{template.docker_image_tag})")

            # Find ssh key 
            ssh_keys = await self._client.ssh_keys.list()
            if len(ssh_keys) == 0:
                raise Exception("No ssh keys found, please add a ssh key to your account")
            logger.debug(f"Found {len(ssh_keys)} ssh keys")

            # Create the pod
            return await self.create(executors[0].id, pod_name or f"lium-pod-{uuid.uuid4()}", template.id, [ssh_keys[0].public_key])
        except Exception as e:
            if template and is_one_time_template:
                await self._client.templates.delete(template.id)
            logger.error(f"Error deploying pod: {e}")
            raise e
    
