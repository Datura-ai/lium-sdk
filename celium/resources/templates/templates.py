import time
import uuid
from uuid import UUID
from celium.utils.docker import build_and_push_docker_image_from_dockerfile, verify_docker_image_validity
from celium.utils.logging import logger
from celium.models.template import Template, TemplateCreate, TemplateUpdate
from celium.resources.base import BaseResource
from celium.resources.templates.templates_core import _TemplatesCore


class Templates(BaseResource, _TemplatesCore):
    """
    Resource to manage templates.
    """
    def create(self, data: TemplateCreate | dict) -> Template:
        """
        Create a template.

        :param data: The data for the new template.
        :type data: TemplateCreate or dict
        :return: The created Template object.
        :rtype: Template
        """
        resp = self._t.request(
            "POST", self.ENDPOINT, json=self._parse_create_data(data)
        )
        return self.parse_one(self._get_json(resp))
    
    def update(self, id: UUID, data: TemplateUpdate | dict) -> Template:
        """
        Update a template.

        :param id: The UUID of the template to update.
        :type id: UUID
        :param data: The data to update the template with.
        :type data: TemplateUpdate or dict
        :return: The updated Template object.
        :rtype: Template
        """
        resp = self._t.request(
            "PUT", f"{self.ENDPOINT}/{id}", json=self._parse_update_data(data)
        )
        return self.parse_one(self._get_json(resp))

    def list(self) -> list[Template]:
        """
        List all templates.

        :return: A list of Template objects.
        :rtype: list[Template]
        """
        resp = self._t.request("GET", self.ENDPOINT)
        return self.parse_many(self._get_json(resp))
    
    def retrieve(self, id: UUID, wait_until_verified: bool = False) -> Template:
        """
        Retrieve a template.

        :param id: The UUID of the template to retrieve.
        :type id: UUID
        :param wait_until_verified: Whether to wait until the template is verified.
        :type wait_until_verified: bool, optional
        :return: The retrieved Template object.
        :rtype: Template
        """
        max_retries = 30 if wait_until_verified else 1
        retries = 0
        while retries < max_retries:
            resp = self._t.request("GET", f"{self.ENDPOINT}/{id}")
            template = self.parse_one(self._get_json(resp))
            if template.status in ["VERIFY_SUCCESS", "VERIFY_FAILED"]:
                return template
            logger.debug(
                f"Template {id} not verified yet, current status is {template.status}, retrying... ({retries}/{max_retries})"
            )
            time.sleep(3)
            retries += 1
        return template

    def delete(self, id: UUID) -> None:
        """
        Delete a template.

        :param id: The UUID of the template to delete.
        :type id: UUID
        :return: None
        :rtype: None
        """
        self._t.request("DELETE", f"{self.ENDPOINT}/{id}") 

    def create_from_image_or_dockerfile(self, docker_image: str | None, dockerfile: str | None) -> tuple[bool, Template]:
        """
        Create a template from a docker image or a dockerfile.
        
        :param docker_image: The docker image to create the template from.
        :type docker_image: str or None
        :param dockerfile: The dockerfile to create the template from.
        :type dockerfile: str or None
        :raises Exception: If no docker image or dockerfile is provided.
        :raises Exception: If failed to build and push the docker image.
        :raises Exception: If the docker image is not valid.
        :return: A tuple of (is_one_time_template, created_template).
        :rtype: tuple[bool, Template]
        """
        if not docker_image and not dockerfile:
            raise Exception("No docker image or dockerfile provided.")
        
        is_one_time_template = False
        image_size = None # built image size in bytes
        d_cred = self._client.docker_credentials.get_default()
        
        if not docker_image:
            docker_image = f"{d_cred.username}/celium-template-{uuid.uuid4()}:latest"
            logger.debug(f"No docker image provided, generated new docker image: {docker_image}")
            is_one_time_template = True

        if dockerfile:
            # Build and push the docker image
            is_success, built_image_size = build_and_push_docker_image_from_dockerfile(
                dockerfile, docker_image, d_cred.username, d_cred.password
            )
            if not is_success:
                raise Exception("Failed to build and push the docker image.")
            
            image_size = built_image_size

        # Verify the docker image is valid
        is_verified = verify_docker_image_validity(docker_image)
        if not is_verified:
            raise Exception("Docker image is not valid. Try to update your Dockerfile or provide a valid docker image.")

        # Check if the template exists with same docker image. If it does, return the template id.
        templates = self._client.templates.list()
        for template in templates:
            full_docker_image = f"{template.docker_image}:{template.docker_image_tag}"
            if full_docker_image == docker_image:
                return is_one_time_template, template

        logger.debug(f"Creating template and waiting for verification: {docker_image}")

        # Create the template
        payload = {
            "category": "UBUNTU",
            "description": "",
            "docker_image": docker_image.split(":")[0],
            "docker_image_tag": docker_image.split(":")[1],
            "docker_image_digest": "",
            "entrypoint": "",
            "environment": {},
            "internal_ports": [],
            "is_private": True,
            "name": docker_image,
            "readme": "",
            "startup_commands": "",
            "volumes": ["/workspace"],
            "one_time_template": is_one_time_template,
            "is_temporary": is_one_time_template,
            "docker_image_size": image_size,
            "docker_credential_id": str(d_cred.id),
        }
        resp = self._t.request("POST", self.ENDPOINT, json=payload)
        template = self.parse_one(self._get_json(resp))
        return (is_one_time_template, self.retrieve(template.id, wait_until_verified=True))