from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, hash_password, is_password_hashed, verify_password
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse


async def migrate_existing_passwords(db: AsyncSession) -> None:
    users = (await db.execute(select(User))).scalars().all()
    for user in users:
        if not is_password_hashed(user.password_hash):
            user.password_hash = hash_password(user.password_hash)


async def register_new_user(db: AsyncSession, payload: RegisterRequest) -> User:
    async with db.begin():
        existing_user = (await db.execute(select(User).where(User.username == payload.username))).scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists.")

        user = User(username=payload.username, password_hash=hash_password(payload.password))
        db.add(user)
    await db.refresh(user)
    return user


async def login_user(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    user = (
        await db.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    access_token = create_access_token(user.id)
    return TokenResponse(access_token=access_token, token_type="bearer")
