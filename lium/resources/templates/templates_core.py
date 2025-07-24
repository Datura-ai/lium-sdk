from typing import Any
from lium.models.template import Template, TemplateCreate, TemplateUpdate


class _TemplatesCore:
    ENDPOINT = "/templates"

    def parse_many(self, data: list[dict[str, Any]]) -> list[Template]:
        return [Template.model_validate(r) for r in data]
    
    def parse_one(self, data: dict[str, Any]) -> Template:
        return Template.model_validate(data)

    def _parse_create_data(self, data: TemplateCreate | dict) -> dict:
        if isinstance(data, dict):
            data = TemplateCreate.model_validate(data)
        return data.model_dump(mode='json', exclude_none=True)

    def _parse_update_data(self, data: TemplateUpdate | dict) -> dict:
        if isinstance(data, dict):
            data = TemplateUpdate.model_validate(data)
        return data.model_dump(mode='json', exclude_none=True)
