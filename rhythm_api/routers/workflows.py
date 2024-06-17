from enum import unique, Enum
from typing import Optional

import celery.states
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


@unique
class Status(str, Enum):
    PENDING = celery.states.PENDING
    STARTED = celery.states.STARTED
    SUCCESS = celery.states.SUCCESS
    FAILURE = celery.states.FAILURE
    REVOKED = celery.states.REVOKED
    DONE = 'DONE'
    ACTIVE = 'ACTIVE'
    EXCEPTION = 'EXCEPTION'


def status_query_values(status: Status) -> list[str]:
    ACTIVE_STATES = [celery.states.PENDING, celery.states.STARTED]
    DONE_STATES = [celery.states.SUCCESS, celery.states.FAILURE, celery.states.REVOKED]
    EXCEPTION_STATES = [celery.states.FAILURE, celery.states.REVOKED]
    if status is not None:
        if status == Status.DONE:
            return DONE_STATES
        elif status == Status.ACTIVE:
            return ACTIVE_STATES
        elif status == Status.EXCEPTION:
            return EXCEPTION_STATES
        else:
            return [status.value]


def query_wf_ids(skip, limit, status=None, app_id=None, workflow_ids=None, sort_by=None, sort_order_asc=True):
    query = omit_none({
        'app_id': app_id
    })

    if status is not None:
        query['_status'] = {
            '$in': status_query_values(status)
        }

    # workflow_ids - non-empty list - search only these workflows
    # workflow_ids - None - search all workflows - no filter by _id
    # workflow_ids - empty list - given queries yield no results. results will be an empty list
    # and response will be []
    if workflow_ids is not None:
        query['_id'] = {
            '$in': workflow_ids
        }

    cursor = wf_col.aggregate([
        {
            '$match': query,
        },
        {
            '$facet': {
                "metadata": [
                    {
                        '$count': 'count'
                    }
                ],
                "results": [
                    {
                        '$sort': {
                            'created_at': 1 if sort_order_asc else -1  # 1 for ascending, -1 for descending
                        }
                    },
                    {
                        '$skip': skip,
                    },
                    {
                        '$limit': limit,
                    },
                    {
                        '$project': {
                            '_id': 1
                        }
                    }
                ]
            }
        }
    ])
    # cursor will always yield a dict with metadata and results keys even if there are no results
    result = next(cursor)

    metadata = result['metadata']
    count = metadata[0]['count'] if metadata else 0
    return result['results'], count


@router.get("")
def get_workflows(
    last_task_run: bool = Query(True, description="Include last task run info"),
    prev_task_runs: bool = Query(False, description="Include previous task runs"),
    status: Status = Query(None, description="Filter by workflow status"),
    app_id: Optional[str] = Query(None, description="Application ID to filter by"),
    skip: int = Query(0, description='Number of items to skip. Default is 0.'),
    limit: int = Query(10, description='Number of items to return. Default is 10.'),
    workflow_id: Optional[list[str]] = Query(None, description="Workflow IDs to filter by"),
    sort_by: str = Query(None, description="Sort by"),
    sort_order_asc: bool = Query(False, description="Direction of sort; true-asc, false-desc"),
) -> dict:
    results, total_count = query_wf_ids(skip=skip,
                                        limit=limit,
                                        status=status,
                                        app_id=app_id,
                                        workflow_ids=workflow_id,
                                        sort_by=sort_by,
                                        sort_order_asc=sort_order_asc
                                        )
    wf_ids = [res['_id'] for res in results]
    workflows = []
    for workflow_id in wf_ids:
        try:
            wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
            if wf is not None:
                workflows.append(
                    wf.get_embellished_workflow(
                        last_task_run=last_task_run,
                        prev_task_runs=prev_task_runs,
                        refresh=False
                    )
                )
        except Exception as e:
            print(e)
    return {
        'metadata': {
            'total': total_count,
            'limit': limit,
            'skip': skip
        },
        'results': workflows
    }


@router.get("/counts_by_status")
def workflow_counts_by_status(
    app_id: Optional[str] = Query(None, description="Application ID to filter by")
) -> dict:
    cursor = wf_col.aggregate([
        {
            '$match': {
                'app_id': app_id,
                '_status': {
                    '$ne': None
                }
            }
        },
        {
            '$group': {
                '_id': '$_status',
                'count': {
                    '$sum': 1
                }
            }
        },
        {
            '$project': {
                'status': '$_id',
                'count': 1,
                '_id': 0
            }
        }
    ])
    results = list(cursor)
    counts = {
        celery.states.PENDING: 0,
        celery.states.STARTED: 0,
        celery.states.FAILURE: 0,
        celery.states.REVOKED: 0,
        celery.states.SUCCESS: 0
    }
    for r in results:
        counts[r['status']] = r['count']
    return counts


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
    kwargs: dict = None


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
    status = wf.pause(refresh=False)
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
    status = wf.resume(force=force, args=body.args, refresh=False)
    return status


@router.delete('/{workflow_id}')
def delete_workflow(workflow_id: str):
    results = wf_col.delete_one({'_id': workflow_id})
    return {
        'deleted_count': results.deleted_count
    }
