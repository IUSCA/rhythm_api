import os
from datetime import datetime, date

from celery import Celery
from flask import Flask, request, jsonify, send_file
from flask.json.provider import DefaultJSONProvider
from flask_swagger_ui import get_swaggerui_blueprint
from rhythm_api import celeryconfig
from sca_rhythm import Workflow, WFNotFound


# jsonify - serialize datetime objects into yyyy-mm-ddTHH:mm:ssssss
# https://stackoverflow.com/a/74618781/2580077
class UpdatedJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, date) or isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


celery_app = Celery("tasks")
celery_app.config_from_object(celeryconfig)

app = Flask(__name__)
app.json = UpdatedJSONProvider(app)


@app.route('/api_docs/swagger.json')
def swagger_json():
    # Read before use: http://flask.pocoo.org/docs/0.12/api/#flask.send_file
    return send_file(os.path.join(app.root_path, '..', 'api_docs', 'swagger.json'))


# Define the Swagger UI blueprint
SWAGGER_URL = '/doc'
API_URL = '/api_docs/swagger.json'
swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Rhythm API"
    }
)

# Register the Swagger UI blueprint
app.register_blueprint(swagger_ui_blueprint)

db = celery_app.backend.database
wf_col = db.get_collection('workflow_meta')
task_col = db.get_collection('celery_taskmeta')


def get_boolean_query(req, name, default=False):
    return req.args.get(name, default, type=lambda v: v.lower() == 'true')


def omit_none(d):
    return {k: v for k, v in d.items() if v is not None}


@app.route('/workflow', methods=['GET'])
def get_workflows():
    last_task_run = get_boolean_query(request, 'last_task_run', default=True)
    prev_task_runs = get_boolean_query(request, 'prev_task_runs')
    only_active = get_boolean_query(request, 'only_active')
    project = request.args.get('project')

    if only_active:
        active_tasks = task_col.find({
            'status': {
                '$nin': ['SUCCESS', 'FAILURE', 'REVOKED']
            }
        })
        workflow_ids = [wf_id for t in active_tasks if
                        (wf_id := t.get('kwargs', {}).get('workflow_id', None))]
        # filter by project
        result = wf_col.find({
            'project': project,
            '_id': {
                '$in': workflow_ids
            }
        }, projection=['_id'])
        workflow_ids = [res['_id'] for res in result]
    else:
        query = omit_none({
            'project': project
        })
        workflow_ids = [res['_id'] for res in wf_col.find(query, projection=['_id'])]
    response = []
    for workflow_id in workflow_ids:
        try:
            wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
            if wf is not None:
                response.append(
                    wf.get_embellished_workflow(
                        last_task_run=last_task_run,
                        prev_task_runs=prev_task_runs
                    )
                )
        except Exception as e:
            print(e)

    return jsonify(response)


@app.route('/workflow/<workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    last_task_run = get_boolean_query(request, 'last_task_run')
    prev_task_runs = get_boolean_query(request, 'prev_task_runs')

    try:
        wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
        return jsonify(wf.get_embellished_workflow(last_task_run=last_task_run, prev_task_runs=prev_task_runs))
    except WFNotFound as exc:
        return str(exc), 404


@app.route('/workflow', methods=['POST'])
def create_workflow():
    try:
        body = request.json
        assert body.get('steps', None), 'missing / invalid "steps" in req body'
        assert body.get('name', None), 'missing / invalid "name" in req body'
        assert body.get('project', None), 'missing / invalid "project" in req body'
        assert isinstance(body.get('args', None), list) and len(body['args']) > 0, 'missing / invalid "args" in req ' \
                                                                                   'body'

        wf = Workflow(celery_app=celery_app,
                      steps=body['steps'],
                      name=body.get['name'],
                      project=body['project'],
                      description=body.get('description', None)
                      )
        wf.start(*body['args'])
        return jsonify({'workflow_id': wf.workflow['_id']})
    except AssertionError as exc:
        return str(exc), 400


@app.route('/workflow/<workflow_id>/pause', methods=['POST'])
def pause_workflow(workflow_id):
    wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
    status = wf.pause()
    return jsonify(status)


@app.route('/workflow/<workflow_id>/resume', methods=['POST'])
def resume_workflow(workflow_id):
    force = get_boolean_query(request, 'force')
    body = request.json
    wf = Workflow(celery_app=celery_app, workflow_id=workflow_id)
    status = wf.resume(force=force, args=body.get('args', None))
    return jsonify(status)


@app.route('/workflow/<workflow_id>', methods=['DELETE'])
def delete_workflow(workflow_id):
    results = wf_col.delete_one({'_id': workflow_id})
    return jsonify({
        'deleted_count': results.deleted_count
    })


@app.route("/health")
def index():
    return "OK"


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host="0.0.0.0", debug=True, port=5000)
    # app.run()
