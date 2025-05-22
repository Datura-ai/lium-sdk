from uuid import UUID
from celium.models.template import Template
from celium.resources.base import BaseResource
from celium.resources.templates.templates_core import _TemplatesCore

class AsyncTemplates(BaseResource, _TemplatesCore):
    async def create(self, **template_data) -> Template:
        """Create a template."""
        resp = await self._t.arequest(
            "POST", self.ENDPOINT, json=template_data
        )
        return self.parse_one(self._get_json(resp))
    
    async def update(self, id: UUID, **template_data) -> Template:
        """Update a template."""
        resp = await self._t.arequest(
            "PUT", f"{self.ENDPOINT}/{id}", json=template_data
        )
        return self.parse_one(self._get_json(resp))

    async def list(self) -> list[Template]:
        """List all templates."""
        resp = await self._t.arequest("GET", self.ENDPOINT)
        return self.parse_many(self._get_json(resp))
    
    async def delete(self, id: UUID) -> None:
        """Delete a template."""
        await self._t.arequest("DELETE", f"{self.ENDPOINT}/{id}") 