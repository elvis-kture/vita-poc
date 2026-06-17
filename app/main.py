import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import Settings, get_settings
from app.db.session import build_engine, build_session_factory, init_db
from app.errors import AppError
from app.worker import expiration_worker, stop_worker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = build_engine(app.state.settings.database_url)
    session_factory = build_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory

    await init_db(engine)

    worker_task = None
    if app.state.settings.enable_expiration_worker:
        worker_task = asyncio.create_task(
            expiration_worker(
                session_factory,
                hold_minutes=app.state.settings.hold_minutes,
                interval_seconds=app.state.settings.expiration_worker_interval_seconds,
            )
        )
    app.state.expiration_worker_task = worker_task

    try:
        yield
    finally:
        await stop_worker(worker_task)
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Ticket Booking API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings or get_settings()
    app.include_router(router)

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return app


app = create_app()
