from celery import Celery

from tests import celeryconfig
from sca_rhythm import Workflow

app = Celery("tasks")
app.config_from_object(celeryconfig)
print('\n'.join(app.tasks.keys()))

batch_id = 'test_id'


steps = [
        {
            'name': 'step-1',
            'task': 'tests.tasks.task1'
        },
        {
            'name': 'step-2',
            'task': 'tests.tasks.task2'
        },
        {
            'name': 'step-3',
            'task': 'tests.tasks.task3'
        }
    ]

wf = Workflow(app, steps=steps, name='test_workflow')
wf.start(batch_id)

