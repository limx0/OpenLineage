import os
from unittest.mock import patch

from openlineage.client import OpenLineageClient
from openlineage.client.facet import (
    DataSourceDatasetFacet,
    DocumentationJobFacet,
    ParentRunFacet,
)
from openlineage.client.run import Job, OutputDataset, Run, RunEvent, RunState
from openlineage.prefect.adapter import OpenLineageAdapter
from openlineage.prefect.facets import PrefectRunFacet
from openlineage.prefect.test_utils.tasks import simple_flow


class TestAdapter:
    def setup(self):
        self.adapter = OpenLineageAdapter()
        # prefect.context.update(
        #     **dict(
        #         flow_name="test-flow",
        #         task_name="test-task",
        #         task_run_id="5c6bf446-627b-425d-8cd7-8db027998f42",
        #         flow_run_id="40991413-2cbe-4fd1-92b0-1e9790bbe104",
        #         date=pendulum.DateTime(2021, 1, 1),
        #     )
        # )

    @patch.object(OpenLineageClient, "emit")
    def test_task_started_to_run_event(self, mock_emit):
        result = simple_flow(p=1)
        run_event = mock_emit.call_args.args[0]
        expected = RunEvent(
            eventType=RunState.START,
            eventTime="2021-01-01T00:00:00",
            run=Run(
                runId="5c6bf446-627b-425d-8cd7-8db027998f42",
                facets={
                    "parentRun": ParentRunFacet(
                        run={"runId": "40991413-2cbe-4fd1-92b0-1e9790bbe104"},
                        job={"namespace": "default", "name": "test-flow.test-task"},
                    )
                },
            ),
            job=Job(
                namespace="default",
                name="test-flow.test-task",
                facets={
                    "documentation": DocumentationJobFacet(
                        description="A simple task",
                    )
                },
            ),
            producer="https://github.com/OpenLineage/OpenLineage/tree/0.1.0/integration/prefect",
            inputs=None,
            outputs=None,
        )
        assert run_event == expected

    @patch(
        "openlineage.prefect.adapter.result_location",
        return_value="2021/1/1/fc357b2e.prefect_result",
    )
    @patch.object(OpenLineageClient, "emit")
    def test_task_success_to_run_event(self, mock_emit, _):
        success = self._run_task(task_cls=SuccessTask)
        self.adapter.on_state_update(
            old_state=Running(), new_state=success, task=self.task, task_inputs={}
        )
        run_event = mock_emit.call_args.args[0]
        expected = RunEvent(
            eventType=RunState.COMPLETE,
            eventTime="2021-01-01T00:00:00",
            run=Run(runId="5c6bf446-627b-425d-8cd7-8db027998f42", facets={}),
            job=Job(namespace="default", name="test-flow.test-task", facets={}),
            producer="https://github.com/OpenLineage/OpenLineage/tree/0.1.0/integration/prefect",
            inputs=None,
            outputs=OutputDataset(
                namespace="test-flow",
                name="test_adapter.SuccessTask",
                facets={
                    "prefect_run": PrefectRunFacet(
                        task="test_adapter.SuccessTask",
                        prefect_version="0.15.5",
                        prefect_commit="50b863925be86d27451f4b9d43a5d7d6c62da359",
                        prefect_backend="cloud",
                        openlineage_prefect_version="0.1.0",
                    )
                },
                outputFacets={
                    "output-dataset": DataSourceDatasetFacet(
                        name="test_adapter.SuccessTask-output",
                        uri="2021/1/1/fc357b2e.prefect_result",
                    )
                },
            ),
        )
        assert run_event == expected

    @patch.object(OpenLineageClient, "emit")
    def test_task_failed_to_run_event(self, mock_emit):
        failed = self._run_task(task_cls=ErrorTask)

        self.adapter.on_state_update(
            old_state=Running(),
            new_state=failed,
            task=self.task,
        )
        run_event = mock_emit.call_args.args[0]
        expected = RunEvent(
            eventType=RunState.FAIL,
            eventTime="2021-01-01T00:00:00",
            run=Run(
                runId="5c6bf446-627b-425d-8cd7-8db027998f42",
                facets={},
            ),
            job=Job(
                namespace="default",
                name="test-flow.test-task",
            ),
            producer="https://github.com/OpenLineage/OpenLineage/tree/0.1.0/integration/prefect",
            inputs=None,
            outputs=None,
        )
        assert run_event == expected
