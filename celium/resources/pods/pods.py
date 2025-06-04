"""/containers endpoints."""
from __future__ import annotations
import time
from typing import Any
import uuid

from celium.models.pod import Pod, PodList
from celium.utils.logging import logger
from celium.resources.base import BaseResource
from celium.resources.pods.pods_core import _PodsCore
from celium.models.executor import Executor, ExecutorFilterQuery


class Pods(BaseResource, _PodsCore):
    """
    Resources to manage pods.

    Example usage::

        with celium.Client(api_key=API_KEY) as client:
            client.pods.list_executors()
    """

    def list_executors(self, filter_query: ExecutorFilterQuery | dict | None = None) -> list[Executor]:
        """
        List all executors. These are the machines from subnet that aren't being rented out.

        :param filter_query: Filter query to filter the executors.
        :type filter_query: ExecutorFilterQuery or dict or None
        :return: List of executors.
        :rtype: list[Executor]
        """
        args, kwargs = self._list_executors_params(filter_query)
        resp = self._t.request(*args, **kwargs)
        return self._parse_list_executors_response(self._get_json(resp))
    
    def create(
        self, 
        id_in_site: uuid.UUID, 
        pod_name: str, 
        template_id: uuid.UUID, 
        user_public_key: list[str],
    ) -> Pod:
        """
        Create/Deploy a pod.

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
        resp = self._t.request("POST", f"/executors/{id_in_site}/rent", json={
            "pod_name": pod_name,
            "template_id": str(template_id),
            "user_public_key": user_public_key,
        })
        return self.retrieve(id_in_site)

    def delete(self, id_in_site: uuid.UUID) -> None:
        """
        Delete a pod.

        :param id_in_site: The id of the pod in the site.
        :type id_in_site: uuid.UUID
        :return: None
        """
        self._t.request("DELETE", f"/executors/{id_in_site}/rent")

    def list(self) -> list[PodList]:
        """
        List all pods.

        :return: List of pods.
        :rtype: list[PodList]
        """
        resp = self._t.request("GET", "/pods")
        return self._parse_list_pods_response(self._get_json(resp))
    
    def retrieve(self, id: uuid.UUID, wait_until_running: bool = False, timeout: int = 5 * 60) -> Pod:
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
        resp = self._t.request("GET", f"/pods/{id}")
        elapsed_time = 0
        pod = None
        while elapsed_time < timeout:
            resp = self._t.request("GET", f"/pods/{id}")
            pod = self._parse_pod_response(self._get_json(resp))
            if not wait_until_running or pod.status == "RUNNING":
                return pod
            time.sleep(5)
            elapsed_time += 5
            logger.debug(f"Pod {id} status: {pod.status}, elapsed time: {elapsed_time}s")
        return pod
    
    def easy_deploy(
        self,
        machine_query: str,
        docker_image: str | None = None,
        dockerfile: str | None = None,
        template_id: str | None = None,
        additional_machine_filter: dict[str, Any] = {},
        pod_name: str | None = None,
    ) -> Pod:
        """
        Easy deploy a pod. 

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
            executors = self.list_executors(
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
                is_one_time_template, template = self._client.templates.create_from_image_or_dockerfile(
                    docker_image, dockerfile
                )
            else:
                template = self._client.templates.retrieve(template_id)
            logger.debug(f"Found template: {template.name}({template.id}-{template.docker_image}:{template.docker_image_tag})")

            # Find ssh key 
            ssh_keys = self._client.ssh_keys.list()
            if len(ssh_keys) == 0:
                raise Exception("No ssh keys found, please add a ssh key to your account")
            logger.debug(f"Found {len(ssh_keys)} ssh keys")

            # Create the pod
            return self.create(executors[0].id, pod_name or f"celium-pod-{uuid.uuid4()}", template.id, [ssh_keys[0].public_key])
        except Exception as e:
            if template and is_one_time_template:
                self._client.templates.delete(template.id)
            logger.error(f"Error deploying pod: {e}")
            raise e

    def list_machines(
        self,
        gpu_type: str | None = None,
        min_gpu_count: int | None = None,
        max_gpu_count: int | None = None,
        max_price_per_hour: float | None = None,
        min_price_per_hour: float | None = None,
        sort_by: str = "price",  # Options: "price", "gpu_count", "uptime"
        sort_order: str = "asc",  # Options: "asc", "desc"
        min_uptime_minutes: int | None = None,
        max_uptime_minutes: int | None = None,
        lat: float | None = None,
        lon: float | None = None,
        max_distance_mile: float | None = None,
    ) -> list[Executor]:
        """
        List available machines with a user-friendly interface.

        This function provides an easy way to find available machines based on various criteria.
        It supports filtering by GPU type, count, price, and uptime, as well as sorting options.

        :param gpu_type: Filter by GPU type (e.g., "A6000", "H100", "A100"). Can be a comma-separated list.
                        Examples: "A6000", "H100,A100", "RTX 4090"
        :type gpu_type: str or None
        :param min_gpu_count: Minimum number of GPUs required
        :type min_gpu_count: int or None
        :param max_gpu_count: Maximum number of GPUs required
        :type max_gpu_count: int or None
        :param max_price_per_hour: Maximum price per hour
        :type max_price_per_hour: float or None
        :param min_price_per_hour: Minimum price per hour
        :type min_price_per_hour: float or None
        :param sort_by: Field to sort results by. Options: "price", "gpu_count", "uptime"
        :type sort_by: str
        :param sort_order: Sort order. Options: "asc" (ascending) or "desc" (descending)
        :type sort_order: str
        :param min_uptime_minutes: Minimum uptime in minutes
        :type min_uptime_minutes: int or None
        :param max_uptime_minutes: Maximum uptime in minutes
        :type max_uptime_minutes: int or None
        :return: List of available machines matching the criteria
        :rtype: list[Executor]

        Example usage:
            >>> with celium.Client() as client:
            ...     # List all A6000 machines
            ...     machines = client.pods.list_machines(gpu_type="A6000")
            ...     
            ...     # List machines with 2-4 GPUs, sorted by price
            ...     machines = client.pods.list_machines(
            ...         min_gpu_count=2,
            ...         max_gpu_count=4,
            ...         sort_by="price",
            ...         sort_order="asc"
            ...     )
            ...     
            ...     # List machines under $5/hour with at least 1 hour uptime
            ...     machines = client.pods.list_machines(
            ...         max_price_per_hour=5.0,
            ...         min_uptime_minutes=60
            ...     )
            ...     
            ...     # List multiple GPU types, sorted by GPU count
            ...     machines = client.pods.list_machines(
            ...         gpu_type="H100,A100",
            ...         sort_by="gpu_count",
            ...         sort_order="desc"
            ...     )
        """
        filter_query = {}
        
        if gpu_type:
            filter_query["machine_names"] = gpu_type.split(",")
        
        if min_gpu_count is not None:
            filter_query["gpu_count_gte"] = min_gpu_count
            
        if max_gpu_count is not None:
            filter_query["gpu_count_lte"] = max_gpu_count
            
        if max_price_per_hour is not None:
            filter_query["price_per_hour_lte"] = max_price_per_hour
            
        if min_price_per_hour is not None:
            filter_query["price_per_hour_gte"] = min_price_per_hour

        if min_uptime_minutes is not None:
            filter_query["uptime_minutes_gte"] = min_uptime_minutes

        if max_uptime_minutes is not None:
            filter_query["uptime_minutes_lte"] = max_uptime_minutes
        
        location_params = [lat, lon, max_distance_mile]
        if any(location_params) and not all(location_params):
            raise ValueError("lat, lon, and max_distance_mile must all be provided together or not at all.")
        
        # Filter by location
        if lat is not None:
            filter_query["lat"] = lat
        if lon is not None:
            filter_query["lon"] = lon
        if max_distance_mile is not None:
            filter_query["max_distance_mile"] = max_distance_mile

        # Get the executors
        executors = self.list_executors(filter_query)

        # Sort the results
        if sort_by == "price":
            executors.sort(key=lambda x: x.price_per_hour, reverse=(sort_order == "desc"))
        elif sort_by == "gpu_count":
            executors.sort(key=lambda x: x.specs.gpu.count, reverse=(sort_order == "desc"))
        elif sort_by == "uptime":
            executors.sort(key=lambda x: x.uptime_in_minutes or 0, reverse=(sort_order == "desc"))

        return executors

