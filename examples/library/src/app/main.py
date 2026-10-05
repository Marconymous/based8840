"""Entry point for `fastapi dev src/app/main.py`. Crashes at import if APP_ENV is missing."""

import os
from typing import Final

from fastapi import FastAPI

from app.core.settings import CONFIG_DIR, load_config
from app.factory import create_app

app: Final[FastAPI] = create_app(load_config(config_dir=CONFIG_DIR, environ=os.environ))
