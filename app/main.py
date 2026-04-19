from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, SessionLocal, engine
from app.routes.auth import router as auth_router
from app.routes.wallets import router as wallets_router
from app.services.auth_service import migrate_existing_passwords


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        async with db.begin():
            await migrate_existing_passwords(db)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(wallets_router)
