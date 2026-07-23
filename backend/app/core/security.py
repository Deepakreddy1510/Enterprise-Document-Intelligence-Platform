from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.models import User

password_hash = PasswordHash.recommended()


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return password_hash.verify(value, hashed)


def create_token(user_id: str) -> str:
    s = get_settings()
    return jwt.encode(
        {
            "sub": user_id,
            "exp": datetime.now(UTC) + timedelta(minutes=s.jwt_access_token_expire_minutes),
        },
        s.jwt_secret_key,
        algorithm=s.jwt_algorithm,
    )


async def current_user(
    access_token: str | None = Cookie(default=None), session: AsyncSession = Depends(get_session)
) -> User:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        payload = jwt.decode(
            access_token, get_settings().jwt_secret_key, algorithms=[get_settings().jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc
    user = await session.scalar(select(User).where(User.id == payload.get("sub")))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user
