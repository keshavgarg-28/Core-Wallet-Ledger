from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.logger import get_logger, setup_logging
from app.middleware import ExceptionHandlingMiddleware
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
        await conn.execute(text("ALTER TABLE wallets ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 0"))
        logger.info("Database tables ensured.")

    async with SessionLocal() as db:
        async with db.begin():
            await migrate_existing_passwords(db)
            logger.info("User password migration check completed.")
    yield
    logger.info("Application shutdown completed.")


app = FastAPI(lifespan=lifespan)
app.add_middleware(ExceptionHandlingMiddleware)
app.include_router(auth_router)
app.include_router(wallets_router)
