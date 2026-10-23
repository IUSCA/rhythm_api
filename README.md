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

`<app-id>` must be the `app_id` the application sends. A token may only list, create, and act on workflows whose `app_id` equals its `sub`.

### App scope
`APP_SCOPE_MODE` in `.env` sets how a token's `sub` is checked against the `app_id` of each request and workflow:
- `log` (default): every request goes through unchanged, and each mismatch is logged as `APP_SCOPE_MISMATCH` with the token's `sub`, the `app_id`, and the route.
- `enforce`: a list, count, or create for another app answers 403, and an omitted `app_id` defaults to the token's own. Another app's workflow answers as if it did not exist.
- `off`: no check.

Deploy in `log` first and read the log (`docker compose logs api | grep APP_SCOPE_MISMATCH`) before switching to `enforce`. Tokens that need every app's workflows, such as an operator's, are listed by `sub` in `APP_SCOPE_ADMIN_SUBJECTS`, comma-separated. Issue one with `--sub <name>` and add the name there.


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
