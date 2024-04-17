import importlib
import os

from dotenv import load_dotenv

from rhythm_api import utils
from rhythm_api.config.common import config

load_dotenv()  # take environment variables from .env.

env = os.environ.get('APP_ENV', None)
if env:
    env_module = importlib.import_module(f'rhythm_api.config.{env}')
    config = utils.merge(common.config, env_module.config)
else:
    config = common.config
