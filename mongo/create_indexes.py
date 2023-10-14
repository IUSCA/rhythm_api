import pymongo

from rhythm_api.config.celeryconfig import result_backend

client = pymongo.MongoClient(result_backend)
db = client['celery']


def create_indexes_on_tasks_collection():
    collection = db.get_collection('celery_taskmeta')
    index_fields = [("status", pymongo.ASCENDING),
                    ("kwargs.app_id", pymongo.ASCENDING),
                    ("kwargs.step", pymongo.ASCENDING)]
    for idx in index_fields:
        collection.create_index(idx)


def create_indexes_on_workflow_collection():
    collection = db.get_collection('workflow_meta')
    index_fields = [("_status", pymongo.ASCENDING),
                    ("app_id", pymongo.ASCENDING)]
    for idx in index_fields:
        collection.create_index(idx)


create_indexes_on_tasks_collection()
create_indexes_on_workflow_collection()
