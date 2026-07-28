import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-enough-length")
from app.core.config import get_settings
from app.core.security import create_token, hash_password, verify_password


def test_password_hash_is_not_plaintext() -> None:
    value = "correct horse battery staple"
    encoded = hash_password(value)
    assert encoded != value
    assert verify_password(value, encoded)
    assert not verify_password("wrong password", encoded)


def test_created_token_has_user_subject() -> None:
    token = create_token("user-id")
    payload = jwt.decode(token, get_settings().jwt_secret_key, algorithms=["HS256"])
    assert payload["sub"] == "user-id"


def test_expired_token_is_rejected() -> None:
    expired = jwt.encode(
        {"sub": "u", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        get_settings().jwt_secret_key,
        algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(expired, get_settings().jwt_secret_key, algorithms=["HS256"])
