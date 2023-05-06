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

### Test
```bash
python -m celery -A tests.tasks worker --concurrency 2
```

This will start celery workers to run tasks in tests.tasks