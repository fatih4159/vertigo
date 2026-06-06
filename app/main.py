"""FastAPI application entry point for AAOS."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config.settings import settings
from app.config.logging import setup_logging
from app.database.session import init_db
from app.core.exceptions import (
    AAOSException,
    AgentNotFoundError,
    AgentStateError,
    ToolExecutionError,
    OllamaConnectionError,
    WorkspaceSecurityError,
)
from app.api.routes import agent, memory, tools, git, models
from app.api.websocket import router as ws_router


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Initialise database tables
    await init_db()
    logger.info("Database ready")

    # Ensure workspace directories exist
    for d in settings.ALLOWED_DIRECTORIES:
        os.makedirs(d, exist_ok=True)
    os.makedirs(settings.WORKSPACE_ROOT, exist_ok=True)
    logger.info("Workspace directories ready")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AGI Agent Operating System - autonomous AI agent platform "
            "with local LLM support via Ollama."
        ),
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(AgentNotFoundError)
    async def agent_not_found(request: Request, exc: AgentNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content=exc.to_dict())

    @app.exception_handler(AgentStateError)
    async def agent_state_error(request: Request, exc: AgentStateError) -> JSONResponse:
        return JSONResponse(status_code=409, content=exc.to_dict())

    @app.exception_handler(ToolExecutionError)
    async def tool_execution_error(request: Request, exc: ToolExecutionError) -> JSONResponse:
        return JSONResponse(status_code=500, content=exc.to_dict())

    @app.exception_handler(OllamaConnectionError)
    async def ollama_error(request: Request, exc: OllamaConnectionError) -> JSONResponse:
        return JSONResponse(status_code=503, content=exc.to_dict())

    @app.exception_handler(WorkspaceSecurityError)
    async def security_error(request: Request, exc: WorkspaceSecurityError) -> JSONResponse:
        return JSONResponse(status_code=403, content=exc.to_dict())

    @app.exception_handler(AAOSException)
    async def aaos_error(request: Request, exc: AAOSException) -> JSONResponse:
        return JSONResponse(status_code=500, content=exc.to_dict())

    # Routers
    prefix = settings.API_PREFIX
    app.include_router(agent.router, prefix=prefix)
    app.include_router(memory.router, prefix=prefix)
    app.include_router(tools.router, prefix=prefix)
    app.include_router(git.router, prefix=prefix)
    app.include_router(models.router, prefix=prefix)
    app.include_router(ws_router)  # WebSocket has no prefix

    # Health
    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
        }

    # Serve built React UI (production / nixpacks deploy)
    ui_dist = Path(__file__).parent.parent / "ui" / "dist"
    if ui_dist.is_dir():
        app.mount("/assets", StaticFiles(directory=ui_dist / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str = "") -> FileResponse:
            # Let API and WS routes through — only catch unmatched paths
            return FileResponse(ui_dist / "index.html")
    else:
        @app.get("/", tags=["system"])
        async def root() -> dict:
            return {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "docs": f"{settings.API_PREFIX}/docs",
                "health": "/health",
                "websocket": "/ws/events",
            }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
