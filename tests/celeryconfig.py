import os
import urllib.parse

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

queue_url = os.environ['QUEUE_URL']
queue_username = os.environ['QUEUE_USER']
queue_password = os.environ['QUEUE_PASS']
mongo_host = os.environ['MONGO_HOST']
mongo_port = os.environ['MONGO_PORT']
mongo_db = os.environ['MONGO_DB']
mongo_auth_source = os.environ['MONGO_AUTH_SOURCE']
mongo_username = os.environ['MONGO_USER']
mongo_password = os.environ['MONGO_PASS']

# https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/rabbitmq.html
broker_url = f'amqp://{queue_username}:{urllib.parse.quote(queue_password)}@{queue_url}'
# task_routes = {
#     'tasksB.task2': 'subtractqueue'
# }

# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-extended
result_extended = True

task_serializer = 'json'
result_serializer = 'json'

# https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html#results
# result_backend = 'redis://localhost:6379/0'

# https://docs.celeryq.dev/en/stable/userguide/configuration.html#conf-mongodb-result-backend
result_backend = f'mongodb://{mongo_username}:{urllib.parse.quote(mongo_password)}@{mongo_host}:{mongo_port}/{mongo_db}?authSource={mongo_db}'

# https://docs.celeryq.dev/en/stable/userguide/configuration.html#database-backend-settings
# https://stackoverflow.com/questions/69952488/celery-task-result-in-postgres-database-is-in-byte-format
# result_backend = 'db+postgresql://username:password@localhost:5432/celery'
