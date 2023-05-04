from urllib.parse import urljoin

import requests


# https://stackoverflow.com/a/51026159/2580077
class APIServerSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.base_url = 'http://localhost:5000'

    def request(self, method, url, *args, **kwargs):
        joined_url = urljoin(self.base_url, url)
        return super().request(method, joined_url, *args, **kwargs)


def test_create_workflow():
    with APIServerSession() as s:
        r = s.post('workflow', json={
            'steps': [
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
            ],
            'args': ['batch_test_id'],
            'name': 'test_workflow'
        })
        print(r)


def test_get_all_workflows():
    with APIServerSession() as s:
        r = s.get('workflow')
        print(r.json())


if __name__ == '__main__':
    # test_create_workflow()
    test_get_all_workflows()


