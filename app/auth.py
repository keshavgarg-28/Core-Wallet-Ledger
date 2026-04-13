import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models import User


load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
PASSWORD_HASH_SCHEME = "bcrypt"
LEGACY_PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
LEGACY_PASSWORD_HASH_ITERATIONS = 100000

security = HTTPBearer()


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_password_hashed(stored_password: str) -> bool:
    return stored_password.startswith("$2") or stored_password.startswith(f"{LEGACY_PASSWORD_HASH_SCHEME}$")


def is_bcrypt_hash(stored_password: str) -> bool:
    return stored_password.startswith("$2")


def verify_legacy_pbkdf2_password(password: str, stored_password_hash: str) -> bool:
    try:
        _, iterations, salt_b64, expected_hash_b64 = stored_password_hash.split("$", maxsplit=3)
        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.b64decode(salt_b64.encode("utf-8")),
            int(iterations),
        )
        actual_hash_b64 = base64.b64encode(derived_key).decode("utf-8")
        return hmac.compare_digest(actual_hash_b64, expected_hash_b64)
    except (ValueError, TypeError):
        return False


def verify_password(password: str, stored_password_hash: str) -> bool:
    if not is_password_hashed(stored_password_hash):
        return False

    if is_bcrypt_hash(stored_password_hash):
        return bcrypt.checkpw(password.encode("utf-8"), stored_password_hash.encode("utf-8"))

    if stored_password_hash.startswith(f"{LEGACY_PASSWORD_HASH_SCHEME}$"):
        return verify_legacy_pbkdf2_password(password, stored_password_hash)

    return False


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
        return user


def authorize_user_access(requested_user_id: str, current_user: User) -> None:
    if requested_user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access another user's wallet.",
        )
