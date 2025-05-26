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
    """Pods resource."""
    
    def list_executors(self, filter_query: ExecutorFilterQuery | dict | None = None) -> list[Executor]:
        """List all executors.
        These are the machines from subnet that aren't being rented out. 
        
        Args:
            filter_query: Filter query to filter the executors.
            
        Returns:
            list[Executor]: List of executors.
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
        """Create a pod.

        Args:
            id_in_site: The id of the pod in the site.
            pod_name: The name of the pod.
            template_id: The id of the template to deploy.
            user_public_key: The user public key to use for the pod.

        Returns:
            Pod: The created pod.
        """
        resp = self._t.request("POST", f"/executors/{id_in_site}/rent", json={
            "pod_name": pod_name,
            "template_id": str(template_id),
            "user_public_key": user_public_key,
        })
        return self.retrieve(id_in_site)

    def delete(self, id_in_site: uuid.UUID) -> None:
        """Delete a pod.
        """
        self._t.request("DELETE", f"/executors/{id_in_site}/rent")

    def list(self) -> list[PodList]:
        """List all pods.

        Returns:
            list[Pod]: List of pods.
        """
        resp = self._t.request("GET", "/pods")
        return self._parse_list_pods_response(self._get_json(resp))
    
    def retrieve(self, id: uuid.UUID, wait_until_running: bool = False, timeout: int = 5 * 60) -> Pod:
        """Retrieve a pod.

        Returns:
            Pod: The retrieved pod.
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
    ) -> None:
        """Easy deploy a template to a machine.

        Args:
            machine_query: The machine query to filter the executors.
            docker_image: The docker image to deploy. Needs to be full image name with tag.
            dockerfile: The dockerfile to deploy.
            additional_machine_filter: Additional machine filter to filter the executors.
            pod_name: The name of the pod.
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

