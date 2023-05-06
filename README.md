# Rhythm API
An API to create and manage workflows using Celery tasks.

This is a ReST API wrapper of [sca_rhythm.Workflow](https://pypi.org/project/sca-rhythm/)

### Set Up Project
- Clone the repo - `git clone` and `cd rhythm_api`
- Install [poetry](https://python-poetry.org/docs/)
- Install dependencies - `poetry install`
- Start Mongo and RabbitMQ - `docker compose up -d mongo queue`
- Start the server - `uvicorn rhythm_api.main:app --reload`


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

### Local API Docs
- [Swagger docs](http://127.0.0.1:8000/docs#/)
- [Open API docs](http://127.0.0.1:8000/redoc)

### Deployment
`bin/deploy.sh`


[Production deployment of Uvicorn](https://www.uvicorn.org/deployment/#gunicorn)
```bash
gunicorn -k uvicorn.workers.UvicornWorker --bind :5001 --workers 1 --threads 1 --timeout 0 rhythm_api.main:app
```

### Test
```bash
python -m celery -A tests.tasks worker --concurrency 2
```

This will start celery workers to run tasks in tests.tasks