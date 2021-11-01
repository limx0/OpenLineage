from typing import Any, Awaitable, Callable, Dict, Optional  # noqa: TYP001

from openlineage.prefect.adapter import OpenLineageAdapter
from prefect.executors import BaseExecutor
from prefect.futures import PrefectFuture
from prefect.orion.schemas.core import TaskRun
from prefect.orion.schemas.states import State
from prefect.utilities.asyncio import A, R

from openlineage.prefect.util import utc_now


class OpenLineageExecutor(BaseExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._adapter = OpenLineageAdapter()
        # Ensure we can connect early - don't want this to trigger tasks to fail inside the flow
        # self._adapter.ping()

    async def submit(
        self,
        task_run: TaskRun,
        run_fn: Callable[..., Awaitable[State[R]]],
        run_kwargs: Dict[str, Any],
        asynchronous: A = True,
    ) -> PrefectFuture[R, A]:
        future = super().submit(
            task_run=task_run,
            run_fn=run_fn,
            run_kwargs=run_kwargs,
            asynchronous=asynchronous,
        )
        self._adapter.start_task(
            run_id=str(task_run.id),
            job_name=run_kwargs['task'].name,
            job_description=run_kwargs['task'].description,
            event_time=utc_now(),
        )
        return future

    async def wait(
        self, prefect_future: PrefectFuture, timeout: float = None
    ) -> Optional[State]:
        state = super().wait(prefect_future=prefect_future)
        return state
