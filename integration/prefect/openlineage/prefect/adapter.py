import os
from typing import Dict, List, Optional, Type  # noqa: TYP001

import prefect
from openlineage.client import OpenLineageClient, set_producer
from openlineage.client.facet import (
    BaseFacet,
    DocumentationJobFacet,
    ParentRunFacet,
    SourceCodeLocationJobFacet,
)
from openlineage.client.run import (
    InputDataset,
    Job,
    OutputDataset,
    Run,
    RunEvent,
    RunState,
)
from openlineage.prefect.util import package_version

_DEFAULT_NAMESPACE = "default"
NAMESPACE = os.getenv("OPENLINEAGE_NAMESPACE", _DEFAULT_NAMESPACE)
OPENLINEAGE_PREFECT_VERSION = package_version()
PRODUCER = f"https://github.com/OpenLineage/OpenLineage/tree/{OPENLINEAGE_PREFECT_VERSION}/integration/prefect"
set_producer(PRODUCER)


class OpenLineageAdapter:
    """
    Adapter for translating prefect task states to OpenLineage events.
    """

    _client = None

    @property
    def client(self) -> OpenLineageClient:
        if not self._client:
            self._client = OpenLineageClient.from_environment()
        return self._client

    @property
    def namespace(self):
        return NAMESPACE

    def ping(self):
        resp = self.client.session.get(self.client.url.replace("5000", "5001"))
        return resp.status_code == 200

    # @staticmethod
    # def task_to_open_lineage_meta(task: Task) -> Dict:
    #     return {
    #         "run_id": context.task_run_id,
    #         "job_name": f"{context.flow_name}.{context.task_name}",
    #     }

    @staticmethod
    def task_inputs_to_input_dataset(
        task_inputs: Dict, inputs_to_tasks: Dict
    ) -> List[InputDataset]:
        return [
            InputDataset(
                namespace=flow_namespace(),
                name=inputs_to_tasks[k],
                facets={},
                inputFacets={},
            )
            for k, v in task_inputs.items()
        ]

    # @staticmethod
    # def task_result_to_output_dataset(task: Task, task_inputs: Dict, result: Result) -> OutputDataset:
    #     output_facets = {}
    #     task_full_name = task_qualified_name(task=task)
    #     if not isinstance(task, Parameter):
    #         output_facets["output-dataset"] = DataSourceDatasetFacet(
    #             name=f"{task_full_name}-output",
    #             uri=result_location(result, **task_inputs),
    #         )
    #     return OutputDataset(
    #         namespace=flow_namespace(),
    #         name=f"{task_full_name}",
    #         facets={"prefect_run": PrefectRunFacet.from_task(task=task)},
    #         outputFacets=output_facets,
    #     )

    def start_task(
        self,
        run_id: str,
        job_name: str,
        job_description: str,
        event_time: str,
        parent_run_id: Optional[str],
        inputs: Optional[List[InputDataset]] = None,
        outputs: Optional[OutputDataset] = None,
        job_facets: Optional[List[BaseFacet]] = None,
        code_location: Optional[str] = None,
        run_facets: Optional[Dict[str, Type[BaseFacet]]] = None,  # Custom run facets
    ) -> str:
        """
        Emits openlineage event of type START
        :param run_id: globally unique identifier of task in dag run
        :param job_name: globally unique identifier of task in dag
        :param job_description: user provided description of job
        :param event_time:
        :param parent_run_id: identifier of job spawning this task
        :param code_location: file path or URL of DAG file
        :param run_facets:
        :return:
        """

        event = RunEvent(
            eventType=RunState.START,
            eventTime=event_time,
            run=self._build_run(run_id, parent_run_id, job_name, run_facets),
            job=self._build_job(job_name, job_description, code_location, job_facets),
            inputs=inputs,
            outputs=outputs,
            producer=PRODUCER,
        )
        self.client.emit(event)
        return event.run.runId

    def complete_task(
        self,
        run_id: str,
        job_name: str,
        end_time: str,
        inputs: Optional[List[InputDataset]] = None,
        outputs: Optional[OutputDataset] = None,
        job_facets: Optional[List[BaseFacet]] = None,
    ):
        """
        Emits openlineage event of type COMPLETE
        :param run_id: globally unique identifier of task in dag run
        :param job_name: globally unique identifier of task between dags
        :param end_time: time of task completion
        """

        event = RunEvent(
            eventType=RunState.COMPLETE,
            eventTime=end_time,
            run=self._build_run(run_id),
            job=self._build_job(job_name, job_facets=job_facets),
            inputs=inputs,
            outputs=outputs,
            producer=PRODUCER,
        )
        self.client.emit(event)

    def fail_task(
        self,
        run_id: str,
        job_name: str,
        end_time: str,
        inputs: Optional[List[InputDataset]] = None,
        outputs: Optional[OutputDataset] = None,
    ):
        """
        Emits openlineage event of type FAIL
        :param run_id: globally unique identifier of task in dag run
        :param job_name: globally unique identifier of task between dags
        :param end_time: time of task completion
        """
        event = RunEvent(
            eventType=RunState.FAIL,
            eventTime=end_time,
            run=self._build_run(run_id),
            job=self._build_job(job_name),
            inputs=inputs,
            outputs=outputs,
            producer=PRODUCER,
        )
        self.client.emit(event)

    @staticmethod
    def _build_run(
        run_id: str,
        parent_run_id: Optional[str] = None,
        job_name: Optional[str] = None,
        custom_facets: Dict[str, Type[BaseFacet]] = None,
    ) -> Run:
        facets = {}
        if parent_run_id:
            facets.update(
                {"parentRun": ParentRunFacet.create(parent_run_id, NAMESPACE, job_name)}
            )

        if custom_facets:
            facets.update(custom_facets)

        return Run(run_id, facets)

    @staticmethod
    def _build_job(
        job_name: str,
        job_description: Optional[str] = None,
        code_location: Optional[str] = None,
        job_facets: Dict[str, BaseFacet] = None,
    ):
        facets = {}

        if job_description:
            facets.update({"documentation": DocumentationJobFacet(job_description)})
        if code_location:
            facets.update(
                {"sourceCodeLocation": SourceCodeLocationJobFacet("", code_location)}
            )
        if job_facets:
            facets = {**facets, **job_facets}

        return Job(NAMESPACE, job_name, facets)


def flow_namespace() -> str:
    """Create a namespace from a flow (and optionally project) name"""
    project = prefect.context.get("project_name")
    prefix = f"{project}." if project else ""
    return f"{prefix}{prefect.context.flow_name}"


# def result_location(result: Result, **raw_inputs) -> str:
#     """Determine results location using the same formatting kwargs prefect does in `task_runner.get_task_run_state`"""
#     formatting_kwargs = {
#         **prefect.context.get("parameters", {}).copy(),
#         **prefect.context,
#         **raw_inputs,
#     }
#     clone = result.copy().format(**formatting_kwargs)
#     return clone.location
#
#
# def task_description(task) -> str:
#     if isinstance(task, Parameter):
#         # Parameters don't have any doc / description at this stage, simply return the name
#         return task.name
#     else:
#         return task.__doc__
