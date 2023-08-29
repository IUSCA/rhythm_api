from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.encoders import ENCODERS_BY_TYPE
from fastapi.responses import JSONResponse
from sca_rhythm import WFNotFound

from rhythm_api.auth import validate_JWT
from rhythm_api.routers import workflows

# https://stackoverflow.com/a/69541044
ENCODERS_BY_TYPE[datetime] = lambda d: d.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

app = FastAPI(title="Rhythm API",
              description="An API to create and manage workflows using Celery tasks")


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
def health():
    return {"health": "OK"}


async def auth(request: Request):
    try:
        authorization = request.headers.get('Authorization', '')
        assert (authorization or '').startswith('Bearer '), 'Invalid token'

        token = authorization.split()[1]
        decoded_token = validate_JWT(token)

        request.state.user = decoded_token['sub']

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


app.include_router(workflows.router, dependencies=[Depends(auth)])


def start_dev():
    uvicorn.run("rhythm_api.main:app", port=5000, log_level="info", reload=True)
