import os
from pathlib import Path
from environ import Env

BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()
Env.read_env(os.path.join(BASE_DIR, ".env"))

REDIS_HOST = env("REDIS_HOST")
REDIS_PORT = env.int("REDIS_PORT")
REDIS_CACHE_DB = env.int("REDIS_CACHE_DB")
REDIS_CELERY_DB = env.int("REDIS_CELERY_DB")

# Redis connection strings
REDIS_CACHE_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CACHE_DB}"
REDIS_CELERY_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
