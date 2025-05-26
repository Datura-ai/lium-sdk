from celium.resources.base import BaseAsyncResource
from celium.resources.pods.pods_core import _PodsCore
from celium.models.executor import Executor, ExecutorFilterQuery    

class AsyncPods(BaseAsyncResource, _PodsCore):
    """Async pods resource."""
    
    async def list_executors(self, filter_query: ExecutorFilterQuery | dict | None = None) -> list[Executor]:
        """List all executors.
        These are the machines from subnet that aren't being rented out. 
        
        Args:
            filter_query: Filter query to filter the executors.
            
        Returns:
            list[Executor]: List of executors.
        """
        args, kwargs = self._list_executors_params(filter_query)
        resp = await self._t.arequest(*args, **kwargs)
        return self._parse_list_executors_response(self._get_json(resp))
