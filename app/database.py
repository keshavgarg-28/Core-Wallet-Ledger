import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, future=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)
Base = declarative_base()

logger.info("Database engine initialized.")
