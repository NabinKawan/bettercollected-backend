"""Application implementation - ASGI."""

from fastapi import FastAPI
from fastapi_pagination import add_pagination
from fastapi_utils.timing import add_timing_middleware
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.responses import JSONResponse

import backend
from backend.app.container import AppContainer, container
from backend.app.handlers import init_logging
from backend.app.handlers.database import init_db, close_db
from backend.app.middlewares import include_middlewares
from backend.config import settings
from backend.app.router import root_api_router
from backend.app.utils import RedisClient, AiohttpClient
from backend.app.exceptions import (
    HTTPException,
    http_exception_handler,
)


async def on_startup():
    """Define FastAPI startup event handler.

    Resources:
        1. https://fastapi.tiangolo.com/advanced/events/#startup-event

    """
    logger.info("Execute FastAPI startup event handler.")
    if settings.USE_REDIS:
        await RedisClient.open_redis_client()

    # Initialize database
    # await init_db(db, client)

    AiohttpClient.get_aiohttp_client()
    # TODO merge with container
    client = container.database_client()
    await init_db(settings.mongo_settings.DB, client)


async def on_shutdown():
    """Define FastAPI shutdown event handler.

    Resources:
        1. https://fastapi.tiangolo.com/advanced/events/#shutdown-event

    """
    logger.info("Execute FastAPI shutdown event handler.")
    # Gracefully close utilities.
    if settings.USE_REDIS:
        await RedisClient.close_redis_client()

    # TODO merge with container
    client = container.database_client()
    await close_db(client)

    await AiohttpClient.close_aiohttp_client()
    await container.http_client.aclose()


def get_application(is_test_mode: bool = False):
    """Initialize FastAPI application.

    Returns:
       FastAPI: Application object instance.

    """
    init_logging()
    container.wire(packages=[backend.app])
    logger.info("Initialize FastAPI application node.")
    api_settings = settings.api_settings
    app = FastAPI(
        title=api_settings.TITLE,
        debug=settings.DEBUG,
        version=api_settings.VERSION,
        docs_url=api_settings.ROOT_PATH + "/docs",
        openapi_url=api_settings.ROOT_PATH + "/openapi.json",
        on_startup=[on_startup],
        on_shutdown=[on_shutdown],
    )
    logger.info("Add application routes.")
    app.include_router(root_api_router)
    logger.info("Register global exception handler for custom HTTPException.")
    app.add_exception_handler(HTTPException, http_exception_handler)

    logger.info("Register application middlewares.")
    include_middlewares(app)
    add_timing_middleware(app, record=logger.info, prefix="app", exclude="untimed")

    if not is_test_mode:
        add_pagination(app)  # Important for paginating elements

    return app
