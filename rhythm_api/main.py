from typing import List, Optional

import uvicorn
from celery import Celery
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sca_rhythm import Workflow, WFNotFound

from rhythm_api import celeryconfig

celery_app = Celery("tasks")
celery_app.config_from_object(celeryconfig)

app = FastAPI(title="Rhythm API",
              description="An API to create and manage workflows using Celery tasks")

db = celery_app.backend.database
wf_col = db.get_collection('workflow_meta')
task_col = db.get_collection('celery_taskmeta')


def omit_none(d):
    return {k: v for k, v in d.items() if v is not None}


@app.exception_handler(WFNotFound)
def not_found_exception(request: Request, exc: WFNotFound):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc)},
    )


@app.exception_handler(AssertionError)
def assertion_exception(request: Request, exc: AssertionError):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


@app.get("/health")
def read_root():
    return {"health": "OK"}


@app.get("/workflows")
def get_workflows(
    last_task_run: bool = Query(True, description="Include last task run info"),
    prev_task_runs: bool = Query(False, description="Include previous task runs"),
    only_active: bool = Query(False, description="Filter by only active workflows"),
    app_id: Optional[str] = Query(None, description="Application ID to filter by")
) -> List[dict]:
    if only_active:
        active_tasks = task_col.find({
            'status': {
                '$nin': ['SUCCESS', 'FAILURE', 'REVOKED']
            }
        })
        workflow_ids = [wf_id for t in active_tasks if
                        (wf_id := (t.get('kwargs', None) or {}).get('workflow_id', None))]
        # filter by application
        result = wf_col.find({
            'app_id': app_id,
            '_id': {
                '$in': workflow_ids
            }
        }, projection=['_id'])
        workflow_ids = [res['_id'] for res in result]
    else:
        query = omit_none({
            'app_id': app_id
        })
        workflow_ids = [res['_id'] for res in wf_col.find(query, projection=['_id'])]
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


@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str,
                 last_task_run: bool = Query(True, description="Include last task run info"),
                 prev_task_runs: bool = Query(False, description="Include previous task runs")
                 ) -> dict:
    wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
    return wf.get_embellished_workflow(last_task_run=last_task_run, prev_task_runs=prev_task_runs)


class WFRequest(BaseModel):
    name: str
    descriptions: str = None
    app_id: str
    steps: list
    args: list


@app.post("/workflows")
def create_workflow(workflow: WFRequest) -> dict:
    body = workflow.dict()
    wf = Workflow(celery_app=celery_app,
                  steps=body['steps'],
                  name=body['name'],
                  app_id=body['app_id'],
                  description=body.get('description', None)
                  )
    wf.start(*body['args'])
    return {'workflow_id': wf.workflow['_id']}


@app.post('/workflows/{workflow_id}/pause')
def pause_workflow(workflow_id: str) -> dict:
    wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
    status = wf.pause()
    return status


class ArgsRequest(BaseModel):
    args: list = None


@app.post('/workflows/{workflow_id}/resume')
def resume_workflow(
    workflow_id: str, 
    args: ArgsRequest, 
    force: bool = Query(False, description="Submit the next task even if its status is not FAILED / REVOKED")
) -> dict:
    body = args.dict()
    wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
    status = wf.resume(force=force, args=body.get('args', None))
    return status


@app.delete('/workflows/{workflow_id}')
def delete_workflow(workflow_id: str):
    results = wf_col.delete_one({'_id': workflow_id})
    return {
        'deleted_count': results.deleted_count
    }


def start_dev():
    uvicorn.run("rhythm_api.main:app", port=5000, log_level="info", reload=True)
