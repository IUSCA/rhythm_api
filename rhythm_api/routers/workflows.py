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
    limit: int = Query(10, description='Number of items to return. Default is 10.')
) -> list[dict]:
    workflow_ids = None
    if only_active:
        active_tasks = task_col.find({
            'status': {
                '$nin': ['SUCCESS', 'FAILURE', 'REVOKED']
            }
        })
        workflow_ids = [wf_id for t in active_tasks if
                        (wf_id := (t.get('kwargs', None) or {}).get('workflow_id', None))]

    query = omit_none({
        'app_id': app_id
    })
    if workflow_ids is not None:
        query['_id'] = {
            '$in': workflow_ids
        }
    results = wf_col.find(query, projection=['_id']).skip(skip).limit(limit)
    workflow_ids = [res['_id'] for res in results]
    response = []
    for workflow_id in workflow_ids:
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


class WFRequest(BaseModel):
    name: str
    description: str = None
    app_id: str
    steps: list
    args: list


@router.post("")
def create_workflow(body: WFRequest) -> dict:
    wf = Workflow(celery_app=celery_app,
                  steps=body.steps,
                  name=body.name,
                  app_id=body.app_id,
                  description=body.description
                  )
    wf.start(*body['args'])
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
