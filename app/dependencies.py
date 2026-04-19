from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import authorize_user_access, get_current_user
from app.database import SessionLocal
from app.logger import get_logger

logger = get_logger(__name__)

async def get_authorized_user(user_id: str, current_user = Depends(get_current_user)):
    authorize_user_access(user_id, current_user)
    return current_user


async def get_db():
    db: AsyncSession = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session.")
        await db.close()
