from typing import Any, Callable, Dict, Optional

from prefect.utilities.asyncio import A

from openlineage.prefect.adapter import OpenLineageAdapter
from prefect.executors import BaseExecutor
from prefect.futures import PrefectFuture
from prefect.orion.schemas.core import TaskRun
from prefect.orion.schemas.states import State, StateType


def parse_task_inputs(inputs: Dict):
    def _parse_task_input(x):
        # TODO - need to look up TaskRunResult output DataDocument
        return x

    return {k: _parse_task_input(v) for k, v in inputs.items()}


def on_submit(method, adapter: OpenLineageAdapter):
    async def inner(
        self: BaseExecutor,
        task_run: TaskRun,
        run_fn: Callable[..., State],
        run_kwargs: Dict[str, Any],
        asynchronous: A = True,
    ) -> PrefectFuture:
        adapter.start_task(task=run_kwargs["task"], task_run=task_run, run_kwargs=run_kwargs)
        future = await method(
            self=self, task_run=task_run, run_fn=run_fn, run_kwargs=run_kwargs, asynchronous=asynchronous,
        )
        return future

    return inner


def on_wait(method, adapter: OpenLineageAdapter):
    async def inner(
        self: BaseExecutor, prefect_future: PrefectFuture, timeout: float = None
    ):
        result = await method(self=self, prefect_future=prefect_future, timeout=timeout)
        if result.type == StateType.COMPLETED:
            adapter.complete_task(result=result)
        elif result.TYPE == StateType.FAILED:
            adapter.fail_task(result=result)
        return result

    return inner


def track_lineage(cls: BaseExecutor, open_lineage_url: Optional[str] = None):
    adapter = OpenLineageAdapter()
    cls.submit = on_submit(cls.submit, adapter=adapter)
    cls.wait = on_wait(cls.wait, adapter=adapter)
    return cls
