import asyncio
from uuid import UUID
from celium.utils.logging import logger
from celium.models.template import Template, TemplateCreate, TemplateUpdate
from celium.resources.base import BaseResource
from celium.resources.templates.templates_core import _TemplatesCore


class AsyncTemplates(BaseResource, _TemplatesCore):
    async def create(self, data: TemplateCreate | dict) -> Template:
        """Create a template."""
        resp = await self._t.arequest(
            "POST", self.ENDPOINT, json=self._parse_create_data(data)
        )
        return self.parse_one(self._get_json(resp))
    
    async def update(self, id: UUID, data: TemplateUpdate | dict) -> Template:
        """Update a template."""
        resp = await self._t.arequest(
            "PUT", f"{self.ENDPOINT}/{id}", json=self._parse_update_data(data)
        )
        return self.parse_one(self._get_json(resp))

    async def list(self) -> list[Template]:
        """List all templates."""
        resp = await self._t.arequest("GET", self.ENDPOINT)
        return self.parse_many(self._get_json(resp))
    
    async def retrieve(self, id: UUID, wait_until_verified: bool = False) -> Template:
        """Retrieve a template."""
        max_retries = 30 if wait_until_verified else 1
        retries = 0
        while retries < max_retries:
            resp = await self._t.arequest("GET", f"{self.ENDPOINT}/{id}")
            template = self.parse_one(self._get_json(resp))
            if template.status in ["VERIFY_SUCCESS", "VERIFY_FAILED"]:
                return template
            logger.debug(
                f"Template {id} not verified yet, current status is {template.status}, retrying... ({retries}/{max_retries})"
            )
            await asyncio.sleep(3)
            retries += 1
        return template
    
    async def delete(self, id: UUID) -> None:
        """Delete a template."""
        await self._t.arequest("DELETE", f"{self.ENDPOINT}/{id}") 