"""FastAPI application factory.

`create_app()` exists (instead of building the app at import time inside a
script) so tests can construct fresh, isolated app instances and override
dependencies on them.
"""

import logging

from fastapi import FastAPI

from citegrep import __version__
from citegrep.api.health import router as health_router
from citegrep.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    application = FastAPI(title="DocuMind", version=__version__)
    application.include_router(health_router)
    return application


app = create_app()
