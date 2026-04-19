from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.logger import get_logger
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import login_user, register_new_user

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Register endpoint called for username=%s.", payload.username)
    return await register_new_user(db, payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Login endpoint called for username=%s.", payload.username)
    return await login_user(db, payload)
