from uuid import UUID
from celium.models.template import Template
from celium.resources.base import BaseResource
from celium.resources.templates.templates_core import _TemplatesCore

class Templates(BaseResource, _TemplatesCore):
    def create(self, **template_data) -> Template:
        """Create a template."""
        resp = self._t.request(
            "POST", self.ENDPOINT, json=template_data
        )
        return self.parse_one(self._get_json(resp))
    
    def update(self, id: UUID, **template_data) -> Template:
        """Update a template."""
        resp = self._t.request(
            "PUT", f"{self.ENDPOINT}/{id}", json=template_data
        )
        return self.parse_one(self._get_json(resp))

    def list(self) -> list[Template]:
        """List all templates."""
        resp = self._t.request("GET", self.ENDPOINT)
        return self.parse_many(self._get_json(resp))

    def delete(self, id: UUID) -> None:
        """Delete a template."""
        self._t.request("DELETE", f"{self.ENDPOINT}/{id}") 