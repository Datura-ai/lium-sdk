from typing import Any

from celium.models.executor import ExecutorFilterQuery, Executor


class _PodsCore:
    ENDPOINT = "/pods"
    EXECUTORS_ENDPOINT = "/executors"

    def _list_executors_params(self, filter_query: ExecutorFilterQuery | None = None) -> tuple[list[Any], dict[str, Any]]:
        return (
            ["GET", self.EXECUTORS_ENDPOINT],
            { "params": filter_query.model_dump(mode='json') if filter_query else None }
        )
    
    def _parse_list_executors_response(self, data: list[dict[str, Any]]) -> list[Executor]:
        return [Executor.model_validate(r) for r in data]