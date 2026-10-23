"""
Scopes each request to the app named by its token's `sub`.

Tokens are issued with `--sub <app-id>`, so `sub` already names the app a token
belongs to. A token may only list, count, create and act on workflows whose
`app_id` equals its `sub`. Subjects listed in `admin_subjects` keep access to
every app.

`mode` controls what happens on a mismatch:
- `off`: no check at all.
- `log`: log the mismatch and let the request through unchanged. Use this first,
  to find callers that would break.
- `enforce`: refuse it. A list, count or create naming another app answers 403;
  a workflow of another app answers 404, as if it did not exist.
"""
import logging
from typing import Optional

from fastapi import HTTPException, Request
from sca_rhythm import WFNotFound

from rhythm_api.config import config

MODES = ('off', 'log', 'enforce')

logger = logging.getLogger('rhythm_api.app_scope')
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def mode() -> str:
    m = config['auth']['app_scope']['mode']
    assert m in MODES, f'auth.app_scope.mode must be one of {MODES}, not {m!r}'
    return m


def is_admin(sub: str) -> bool:
    return sub in config['auth']['app_scope']['admin_subjects']


def _log_mismatch(request: Request, sub: str, app_id: Optional[str], workflow_id: Optional[str] = None):
    logger.warning('APP_SCOPE_MISMATCH mode=%s sub=%s app_id=%s workflow_id=%s route="%s %s"',
                   mode(), sub, app_id, workflow_id, request.method, request.url.path)


def resolve_app_id(request: Request, app_id: Optional[str]) -> Optional[str]:
    """
    Returns the app_id a list, count or create request should use.

    An omitted app_id defaults to the token's own app under `enforce`. Under `log`
    it stays omitted, as before, and is logged.
    """
    sub = request.state.user
    if mode() == 'off' or is_admin(sub) or app_id == sub:
        return app_id

    _log_mismatch(request, sub, app_id)
    if mode() == 'log':
        return app_id
    if app_id is None:
        return sub
    raise HTTPException(status_code=403, detail=f'This token may only use app_id {sub}')


def check_workflow(request: Request, workflow_id: str, wf_app_id: Optional[str]):
    """Refuses access to a workflow of another app, under `enforce`, with the same 404 a missing one gets."""
    sub = request.state.user
    if mode() == 'off' or is_admin(sub) or wf_app_id == sub:
        return

    _log_mismatch(request, sub, wf_app_id, workflow_id)
    if mode() == 'enforce':
        raise WFNotFound(f'Workflow with id {workflow_id} is not found')
