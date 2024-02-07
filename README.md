# Rhythm API
An API to create and manage workflows using Celery tasks.

This is a ReST API wrapper of [sca_rhythm.Workflow](https://pypi.org/project/sca-rhythm/)


### Set Up Project
- Clone the repo - `git clone` and `cd rhythm_api`
- Generate Keys: `cd keys; ./genkeys.sh`
- Create .env: `cp .env.example .env`
- Start the server - `docker compose up -d mongo queue api`

### Set Up Project - without docker
- Clone the repo - `git clone` and `cd rhythm_api`
- Install [poetry](https://python-poetry.org/docs/)
- Start Mongo and RabbitMQ - `docker compose up -d`
- Generate Keys: `cd keys; ./genkeys.sh`
- Create .env: `cp .env.example .env`
- Start the server - `poetry run dev` or `uvicorn rhythm_api.main:app --reload`

### Backup MongoDB
```bash
docker compose run --rm mongobackup
```
Backup are in db/backups


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
- [Swagger docs](http://127.0.0.1:5000/docs#/)
- [Open API docs](http://127.0.0.1:5000/redoc)

### Issue token
```bash
sudo docker compose -f "docker-compose-prod.yml" exec api python -m rhythm_api.scripts.issue_token --sub <app-id>
```


[Production deployment of Uvicorn](https://www.uvicorn.org/deployment/#gunicorn)
```bash
gunicorn -k uvicorn.workers.UvicornWorker --bind :5001 --workers 1 --threads 1 --timeout 0 rhythm_api.main:app
```

### Test
```bash
python -m celery -A tests.tasks worker --concurrency 2
```

This will start celery workers to run tasks in tests.tasks


### Poetry bug

`poetry update` is not installing the latest version of `sca-rhythm`. The workaround is
- update `pyproject.toml` with the latest version of `sca-rhythm`
- `pip uninstall sca-rhythm`
- `poetry cache clear pypi --all`
- poetry update