import json

from openlineage.prefect.executor import OpenLineageExecutor
from openlineage.prefect.test_utils import RESOURCES
from prefect import flow, task


@task()
def get(n):
    """
    Get a json file
    """
    filename = f"{RESOURCES}/{n}.json"
    return json.loads(open(filename).read())


@task()
def inc(g):
    return g + 1


@task()
def multiply(i):
    """
    Multiple the value
    """
    return i * 2


@task()
def non_data_task(m):
    return


@task()
def error_task():
    raise ValueError("custom-error-message")


@flow(executor=OpenLineageExecutor())
def simple_flow(p: str):
    g = get(p)
    i = inc(g)
    m = multiply(i)
    non_data_task(m)


@flow(executor=OpenLineageExecutor())
def error_flow():
    return error_task()
