from celery import Celery
from fastapi import APIRouter, Query

from rhythm_api.config import celeryconfig

celery_app = Celery("tasks")
celery_app.config_from_object(celeryconfig)

db = celery_app.backend.database
task_col = db.get_collection('celery_taskmeta')

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


# @router.get("/active")
# def group_active_tasks_by_step(app_id: str = Query(description="Application ID")) -> list[dict]:
#     cursor = task_col.aggregate(
#         [
#             {
#                 '$match': {
#                     'kwargs.step': {'$ne': None},
#                     'kwargs.app_id': app_id,
#                     'status': {'$nin': [celery.states.SUCCESS]}
#                 }
#             },
#             {
#                 '$group': {
#                     '_id': '$kwargs.step',
#                     'tasks': {'$push': '$$ROOT'}
#                 }
#             },
#             {
#                 '$project': {
#                     'step': "$_id",
#                     'tasks': 1,
#                     '_id': 0
#                 }
#             }
#
#         ]
#     )
#     return list(cursor)


@router.get('/unique')
def unique_steps(app_id: str = Query(description="Application ID")) -> list:
    cursor = task_col.distinct('kwargs.step')
    return list(cursor)
