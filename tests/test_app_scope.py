"""
Tests for rhythm_api/app_scope.py through the workflows router, with Celery and
MongoDB replaced by fakes. Run with: pytest tests/test_app_scope.py
"""
import logging
import os

for _k, _v in {'QUEUE_URL': 'queue:5672/test', 'QUEUE_USER': 'u', 'QUEUE_PASS': 'p', 'MONGO_HOST': 'localhost',
               'MONGO_PORT': '27017', 'MONGO_DB': 'celery', 'MONGO_AUTH_SOURCE': 'admin', 'MONGO_USER': 'u',
               'MONGO_PASS': 'p'}.items():
    os.environ.setdefault(_k, _v)

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sca_rhythm import WFNotFound

from rhythm_api.config import config
from rhythm_api.routers import workflows

APP_A = 'a.example.org'
APP_B = 'b.example.org'
ADMIN = 'operator'


class FakeWorkflow:
    store = {}

    def __init__(self, celery_app, workflow_id=None, steps=None, name=None, app_id=None, description=None):
        if workflow_id is not None:
            if workflow_id not in self.store:
                raise WFNotFound(f'Workflow with id {workflow_id} is not found')
            self.workflow = self.store[workflow_id]
        else:
            self.workflow = {'_id': 'wf-new', 'app_id': app_id}

    def get_embellished_workflow(self, **kwargs):
        return dict(self.workflow)

    def pause(self, refresh=False):
        return {'paused': True}

    def resume(self, force=False, args=None, refresh=False):
        return {'resumed': True}

    def start(self, *args):
        FakeWorkflow.store[self.workflow['_id']] = self.workflow


class FakeDeleteResult:
    def __init__(self, n):
        self.deleted_count = n


class FakeCollection:
    def __init__(self):
        self.last_match = None

    def find_one(self, query, projection=None):
        return FakeWorkflow.store.get(query['_id'])

    def delete_one(self, query):
        return FakeDeleteResult(1 if FakeWorkflow.store.pop(query['_id'], None) else 0)

    def aggregate(self, pipeline):
        self.last_match = pipeline[0]['$match']
        if '$facet' in pipeline[1]:
            return iter([{'metadata': [], 'results': []}])
        return iter([])


@pytest.fixture
def wf_col(monkeypatch):
    FakeWorkflow.store = {
        'wf-a': {'_id': 'wf-a', 'app_id': APP_A},
        'wf-b': {'_id': 'wf-b', 'app_id': APP_B},
    }
    col = FakeCollection()
    monkeypatch.setattr(workflows, 'Workflow', FakeWorkflow)
    monkeypatch.setattr(workflows, 'wf_col', col)
    monkeypatch.setitem(config['auth']['app_scope'], 'admin_subjects', [ADMIN])
    return col


def make_client(monkeypatch, mode):
    monkeypatch.setitem(config['auth']['app_scope'], 'mode', mode)

    async def fake_auth(request: Request):
        request.state.user = request.headers['X-Test-Sub']

    app = FastAPI()

    @app.exception_handler(WFNotFound)
    def not_found(request: Request, exc: WFNotFound):
        return JSONResponse(status_code=404, content={'message': str(exc)})

    app.include_router(workflows.router, dependencies=[Depends(fake_auth)])
    return TestClient(app)


def as_sub(sub):
    return {'X-Test-Sub': sub}


@pytest.fixture
def mismatch_log(caplog):
    logger = logging.getLogger('rhythm_api.app_scope')
    logger.addHandler(caplog.handler)
    yield caplog
    logger.removeHandler(caplog.handler)


def new_wf(app_id):
    return {'name': 'wf', 'app_id': app_id, 'steps': [{'name': 's', 'task': 't', 'queue': 'q'}], 'args': []}


# enforce

def test_enforce_list_defaults_to_own_app(monkeypatch, wf_col):
    c = make_client(monkeypatch, 'enforce')
    assert c.get('/workflows', headers=as_sub(APP_A)).status_code == 200
    assert wf_col.last_match['app_id'] == APP_A


def test_enforce_list_of_other_app_is_refused(monkeypatch, wf_col):
    c = make_client(monkeypatch, 'enforce')
    assert c.get('/workflows', params={'app_id': APP_B}, headers=as_sub(APP_A)).status_code == 403
    assert c.get('/workflows/counts_by_status', params={'app_id': APP_B}, headers=as_sub(APP_A)).status_code == 403


def test_enforce_counts_default_to_own_app(monkeypatch, wf_col):
    c = make_client(monkeypatch, 'enforce')
    assert c.get('/workflows/counts_by_status', headers=as_sub(APP_A)).status_code == 200
    assert wf_col.last_match['app_id'] == APP_A


def test_enforce_own_workflow_is_allowed(monkeypatch, wf_col):
    c = make_client(monkeypatch, 'enforce')
    assert c.get('/workflows/wf-a', headers=as_sub(APP_A)).json()['app_id'] == APP_A
    assert c.post('/workflows/wf-a/pause', headers=as_sub(APP_A)).status_code == 200
    assert c.post('/workflows/wf-a/resume', json={}, headers=as_sub(APP_A)).status_code == 200
    assert c.delete('/workflows/wf-a', headers=as_sub(APP_A)).json() == {'deleted_count': 1}


def test_enforce_other_workflow_looks_missing(monkeypatch, wf_col):
    c = make_client(monkeypatch, 'enforce')
    missing = c.get('/workflows/wf-none', headers=as_sub(APP_A))
    other = c.get('/workflows/wf-b', headers=as_sub(APP_A))
    assert other.status_code == missing.status_code == 404
    assert other.json() == {'message': 'Workflow with id wf-b is not found'}
    assert c.post('/workflows/wf-b/pause', headers=as_sub(APP_A)).status_code == 404
    assert c.post('/workflows/wf-b/resume', json={}, headers=as_sub(APP_A)).status_code == 404
    assert c.delete('/workflows/wf-b', headers=as_sub(APP_A)).json() == \
        c.delete('/workflows/wf-none', headers=as_sub(APP_A)).json() == {'deleted_count': 0}
    assert 'wf-b' in FakeWorkflow.store


def test_enforce_create_for_other_app_is_refused(monkeypatch, wf_col):
    c = make_client(monkeypatch, 'enforce')
    assert c.post('/workflows', json=new_wf(APP_B), headers=as_sub(APP_A)).status_code == 403
    assert c.post('/workflows', json=new_wf(APP_A), headers=as_sub(APP_A)).status_code == 200


def test_enforce_admin_reaches_every_app(monkeypatch, wf_col):
    c = make_client(monkeypatch, 'enforce')
    assert c.get('/workflows', params={'app_id': APP_B}, headers=as_sub(ADMIN)).status_code == 200
    assert wf_col.last_match['app_id'] == APP_B
    assert c.get('/workflows', headers=as_sub(ADMIN)).status_code == 200
    assert 'app_id' not in wf_col.last_match
    assert c.get('/workflows/wf-b', headers=as_sub(ADMIN)).status_code == 200


# log

def test_log_lets_everything_through_and_logs_it(monkeypatch, wf_col, mismatch_log):
    c = make_client(monkeypatch, 'log')
    assert c.get('/workflows/wf-b', headers=as_sub(APP_A)).status_code == 200
    assert c.post('/workflows', json=new_wf(APP_B), headers=as_sub(APP_A)).status_code == 200
    assert c.get('/workflows', headers=as_sub(APP_A)).status_code == 200
    assert 'app_id' not in wf_col.last_match  # unchanged: an omitted app_id still lists every app
    lines = [r.getMessage() for r in mismatch_log.records if 'APP_SCOPE_MISMATCH' in r.getMessage()]
    assert len(lines) == 3
    assert f'sub={APP_A} app_id={APP_B} workflow_id=wf-b route="GET /workflows/wf-b"' in lines[0]


def test_log_is_quiet_for_own_app(monkeypatch, wf_col, mismatch_log):
    c = make_client(monkeypatch, 'log')
    c.get('/workflows', params={'app_id': APP_A}, headers=as_sub(APP_A))
    c.get('/workflows/wf-a', headers=as_sub(APP_A))
    assert not [r for r in mismatch_log.records if 'APP_SCOPE_MISMATCH' in r.getMessage()]


# off

def test_off_checks_nothing(monkeypatch, wf_col, mismatch_log):
    c = make_client(monkeypatch, 'off')
    assert c.get('/workflows/wf-b', headers=as_sub(APP_A)).status_code == 200
    assert c.get('/workflows', params={'app_id': APP_B}, headers=as_sub(APP_A)).status_code == 200
    assert not mismatch_log.records


def test_unknown_mode_fails_loudly(monkeypatch, wf_col):
    c = make_client(monkeypatch, 'enforcing')
    with pytest.raises(AssertionError):
        c.get('/workflows/wf-b', headers=as_sub(APP_A))
