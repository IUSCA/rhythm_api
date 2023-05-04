## Worker API
### seed the mongo db
```bash
# PWD - go to project root where the docker-compose.yml is
mkdir -p db/mongodump
cp mongo/*.json db/mongodump/
docker-compose up mongo -d
docker-compose exec mongo bash

$ cd /opt/sca/app/mongodump
$ mongoimport --uri 'mongodb://root:example@localhost:27017/?authSource=admin' --jsonArray --db celery --collection celery_taskmeta --file celery_taskmeta.json
$ mongoimport --uri 'mongodb://root:example@localhost:27017/?authSource=admin' --jsonArray --db celery --collection workflow_meta --file workflow_meta.json
```

### start the api server
```bash
gunicorn -p app.pid --bind :5001 --workers 1 --threads 1 --timeout 0 scaworkers.app:app
```

```bash
python -m scaworkers.app
```


```bash
[2023-03-24 02:36:58,765: ERROR/MainProcess] Received unregistered task of type 'test.tasks.task1'.
The message has been ignored and discarded.

Did you remember to import the module containing this task?
Or maybe you're using relative imports?

Please see
http://docs.celeryq.org/en/latest/internals/protocol.html
for more information.

The full contents of the message body was:
'[["test_id"], {"workflow_id": "870d508b-82b0-45e4-8da3-22c47f42b85b", "step": "step-1"}, {"callbacks": null, "errbacks": null, "chain": null, "chord": null}]' (157b)

Thw full contents of the message headers:
{'lang': 'py', 'task': 'test.tasks.task1', 'id': 'ee054958-fe5d-46f7-9324-88c4696ca42f', 'shadow': None, 'eta': None, 'expires': None, 'group': None, 'group_index': None, 'retries': 0, 'timelimit': [None, None], 'root_id': 'ee054958-fe5d-46f7-9324-88c4696ca42f', 'parent_id': None, 'argsrepr': "('test_id',)", 'kwargsrepr': "{'workflow_id': '870d508b-82b0-45e4-8da3-22c47f42b85b', 'step': 'step-1'}", 'origin': 'gen26183@Deepaks-MacBook-Air.local', 'ignore_result': False}

The delivery info for this task is:
{'consumer_tag': 'None4', 'delivery_tag': 1, 'redelivered': False, 'exchange': '', 'routing_key': 'celery'}
Traceback (most recent call last):
  File "/Users/deepakduggirala/miniforge3/envs/scaworkers/lib/python3.11/site-packages/celery/worker/consumer/consumer.py", line 591, in on_task_received
    strategy = strategies[type_]
               ~~~~~~~~~~^^^^^^^
KeyError: 'test.tasks.task1'
```