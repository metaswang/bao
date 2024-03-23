import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from bao.api.chat_router import chat_router, favicon_router
from bao.api.injest_router import ingest_router
from bao.di import global_injector
from bao.settings.settings import Settings
from bao.web_client.ingest_ui import IngestUI

logger = logging.getLogger(__name__)


def create_fastapi_app() -> FastAPI:

    async def bind_injector_to_request(request: Request) -> None:
        request.state.injector = global_injector

    app = FastAPI(dependencies=[Depends(bind_injector_to_request)])

    app.include_router(favicon_router)
    app.include_router(chat_router)
    app.include_router(ingest_router)

    settings = global_injector.get(Settings)
    if settings.server.cors.enabled:
        logger.debug("CORS settings")
        app.add_middleware(
            CORSMiddleware,
            allow_credentials=settings.server.cors.allow_credentials,
            allow_origins=settings.server.cors.allow_origins,
            allow_origin_regex=settings.server.cors.allow_origin_regex,  # type: ignore
            allow_methods=settings.server.cors.allow_methods,
            allow_headers=settings.server.cors.allow_headers,
        )

    logger.debug("UI module")
    from bao.web_client.chat_ui import ChatUI

    if settings.web_chat.enabled:
        ui_chat = global_injector.get(ChatUI)
        ui_chat.mount_in_app(app, settings.web_chat.path)
    if settings.web_ingest.enabled:
        ui_ingest = global_injector.get(IngestUI)
        ui_ingest.mount_in_app(app, settings.web_ingest.path)

    return app
