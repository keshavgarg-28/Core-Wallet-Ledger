from fastapi import Depends

from app.auth import authorize_user_access, get_current_user


async def get_authorized_user(user_id: str, current_user = Depends(get_current_user)):
    authorize_user_access(user_id, current_user)
    return current_user
