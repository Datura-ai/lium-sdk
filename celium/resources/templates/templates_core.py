from typing import Any
from celium.models.template import Template

class _TemplatesCore:
    ENDPOINT = "/templates"

    def parse_many(self, data: list[dict[str, Any]]) -> list[Template]:
        return [Template.model_validate(r) for r in data]
    
    def parse_one(self, data: dict[str, Any]) -> Template:
        return Template.model_validate(data)
