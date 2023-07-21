from typing import Optional

from celery import Celery
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sca_rhythm import Workflow

from rhythm_api.config import celeryconfig

celery_app = Celery("tasks")
celery_app.config_from_object(celeryconfig)

db = celery_app.backend.database
wf_col = db.get_collection('workflow_meta')
task_col = db.get_collection('celery_taskmeta')


def omit_none(d):
    return {k: v for k, v in d.items() if v is not None}


def pending_workflow_ids(app_id=None):
    query = {
        "app_id": app_id,
        "steps": {
            "$not": {
                "$elemMatch": {
                    "task_runs": {"$exists": True},
                }
            }
        }
    }

    return wf_col.distinct('_id', omit_none(query))


def running_workflow_ids():
    query = {
        'status': {'$nin': ['SUCCESS', 'FAILURE', 'REVOKED']},
        'kwargs.workflow_id': {'$exists': True, '$ne': None}
    }

    return task_col.distinct("kwargs.workflow_id", query)


router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
)


@router.get("")
def get_workflows(
    last_task_run: bool = Query(True, description="Include last task run info"),
    prev_task_runs: bool = Query(False, description="Include previous task runs"),
    only_active: bool = Query(False, description="Filter by only active workflows"),
    app_id: Optional[str] = Query(None, description="Application ID to filter by"),
    skip: int = Query(0, description='Number of items to skip. Default is 0.'),
    limit: int = Query(10, description='Number of items to return. Default is 10.'),
    workflow_id: Optional[list[str]] = Query(None, description="Workflow IDs to filter by"),
) -> list[dict]:
    # if workflow_ids are provided, narrow the search among these workflows
    # else consider all workflows
    if only_active:
        active_workflow_ids = set(pending_workflow_ids(app_id=app_id)) | set(running_workflow_ids())
        if workflow_id is not None:
            wf_id_filter = list(set(workflow_id) & active_workflow_ids)
        else:
            wf_id_filter = list(active_workflow_ids)
    else:
        wf_id_filter = workflow_id

    query = omit_none({
        'app_id': app_id
    })

    # wf_id_filter - non-empty list - search only these workflows
    # wf_id_filter - None - search all workflows - no filter by _id
    # wf_id_filter - empty list - given queries yield no results. results will be an empty list
    # and response will be []
    if wf_id_filter is not None:
        query['_id'] = {
            '$in': wf_id_filter
        }

    results = wf_col.find(query, projection=['_id']).skip(skip).limit(limit)
    wf_ids = [res['_id'] for res in results]
    response = []
    for workflow_id in wf_ids:
        try:
            wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
            if wf is not None:
                response.append(
                    wf.get_embellished_workflow(
                        last_task_run=last_task_run,
                        prev_task_runs=prev_task_runs
                    )
                )
        except Exception as e:
            print(e)
    return response


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str,
                 last_task_run: bool = Query(True, description="Include last task run info"),
                 prev_task_runs: bool = Query(False, description="Include previous task runs")
                 ) -> dict:
    wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
    return wf.get_embellished_workflow(last_task_run=last_task_run, prev_task_runs=prev_task_runs)


class WFStep(BaseModel):
    name: str
    task: str
    queue: str


class WFRequest(BaseModel):
    name: str
    description: str = None
    app_id: str
    steps: list[WFStep]
    args: list


@router.post("")
def create_workflow(body: WFRequest) -> dict:
    steps = [step.dict() for step in body.steps]
    wf = Workflow(celery_app=celery_app,
                  steps=steps,
                  name=body.name,
                  app_id=body.app_id,
                  description=body.description
                  )
    wf.start(*body.args)
    return {'workflow_id': wf.workflow['_id']}


@router.post('/{workflow_id}/pause')
def pause_workflow(workflow_id: str) -> dict:
    wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
    status = wf.pause()
    return status


class ArgsRequest(BaseModel):
    args: list = None


@router.post('/{workflow_id}/resume')
def resume_workflow(
    workflow_id: str,
    body: ArgsRequest,
    force: bool = Query(False, description="Submit the next task even if its status is not FAILED / REVOKED")
) -> dict:
    wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
    status = wf.resume(force=force, args=body.args)
    return status


@router.delete('/{workflow_id}')
def delete_workflow(workflow_id: str):
    results = wf_col.delete_one({'_id': workflow_id})
    return {
        'deleted_count': results.deleted_count
    }
