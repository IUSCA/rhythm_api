import os

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

config = {
    'auth': {
        'jwt': {
            'iss': 'localhost',
            'pub': 'keys/auth.pub',
            'key': 'keys/auth.key',
        },
        # See rhythm_api/app_scope.py. The default, log, changes no response.
        'app_scope': {
            'mode': os.environ.get('APP_SCOPE_MODE', 'log'),
            'admin_subjects': [s.strip() for s in os.environ.get('APP_SCOPE_ADMIN_SUBJECTS', '').split(',') if s.strip()],
        },
    }
}
