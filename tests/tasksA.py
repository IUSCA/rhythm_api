import os
import time

from celery import Celery

from tests import celeryconfig
from sca_rhythm import WorkflowTask

app = Celery("tasks")
app.config_from_object(celeryconfig)


# python -m celery -A tests.tasks worker --concurrency 4
@app.task(base=WorkflowTask, bind=True)
def task1(self, dataset_id, **kwargs):
    print(f'task - {os.getpid()} 1 starts with {dataset_id}')
    time.sleep(1)
    return dataset_id, {'return_obj': 'foo'}


@app.task(base=WorkflowTask, bind=True)
def task2(self, dataset_id, **kwargs):
    print(f'task - {os.getpid()} 2 starts with {dataset_id}')
    i = 0
    while i < 10:
        i = i + 1
        print(i)
        time.sleep(1)
    return dataset_id,


@app.task(base=WorkflowTask, bind=True)
def task3(self, dataset_id, **kwargs):
    print(f'task - {os.getpid()} 3 starts with {dataset_id}')
    time.sleep(1)
    return dataset_id,
