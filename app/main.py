from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request

from app.database import Base, SessionLocal, engine
from app.logger import get_logger, setup_logging
from app.routes.auth import router as auth_router
from app.routes.wallets import router as wallets_router
from app.services.auth_service import migrate_existing_passwords

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup initiated.")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured.")

    async with SessionLocal() as db:
        async with db.begin():
            await migrate_existing_passwords(db)
            logger.info("User password migration check completed.")
    yield
    logger.info("Application shutdown completed.")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = perf_counter()
    logger.info("Request started: %s %s", request.method, request.url.path)
    response = await call_next(request)
    duration_ms = (perf_counter() - start_time) * 1000
    logger.info(
        "Request completed: %s %s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(auth_router)
app.include_router(wallets_router)
