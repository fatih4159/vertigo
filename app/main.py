"""FastAPI application entry point for AAOS."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

async def _reset_transient_agent_states() -> None:
    """Reset agents left in RUNNING/PAUSED state from a previous server run.

    Without live runner instances these agents are frozen and uncontrollable.
    Resetting to STOPPED lets users restart them immediately.
    """
    from datetime import datetime
    from sqlalchemy import update as sql_update
    from app.database.models import Agent
    from app.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        stmt = (
            sql_update(Agent)
            .where(Agent.state.in_(["RUNNING", "PAUSED"]))
            .values(state="STOPPED", updated_at=datetime.utcnow())
        )
        result = await session.execute(stmt)
        await session.commit()
        if result.rowcount:
            logger.warning(
                f"[Startup] Reset {result.rowcount} agent(s) from active state to STOPPED "
                "(no live runners after restart)"
            )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Ensure the SQLite data directory exists before the engine is created
    if settings.DATABASE_URL.startswith("sqlite"):
        from pathlib import Path
        db_path = settings.DATABASE_URL.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Initialise database tables
    await init_db()
    logger.info("Database ready")

    # Recover agents frozen in transient states from a prior unclean shutdown
    await _reset_transient_agent_states()

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
