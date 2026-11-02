"""Krishi Mitra / AgriNova Security and Cryptography Utilities.

Provides password and PIN hashing via PBKDF2-HMAC-SHA256 and JWT token issuance/verification.
No external native dependencies required.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Any, Optional

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedAccessError

PBKDF2_ITERATIONS = 100_000
PBKDF2_ALGORITHM = "sha256"


def hash_pin_or_password(secret: str) -> str:
    """Hash a numeric PIN or textual password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    
    Format: pbkdf2:sha256:100000$<salt_hex>$<hash_hex>
    """
    if not secret:
        raise ValueError("Secret cannot be empty.")
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        secret.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2:{PBKDF2_ALGORITHM}:{PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_pin_or_password(plain_secret: str, hashed_secret: str) -> bool:
    """Verify a plain secret against a stored PBKDF2 hash using constant-time comparison."""
    if not plain_secret or not hashed_secret:
        return False
    try:
        header, salt_hex, expected_hex = hashed_secret.split("$")
        algo_parts = header.split(":")
        if len(algo_parts) != 3 or algo_parts[0] != "pbkdf2":
            return False
        algo = algo_parts[1]
        iterations = int(algo_parts[2])
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(expected_hex)

        derived = hashlib.pbkdf2_hmac(
            algo,
            plain_secret.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(derived, expected_hash)
    except Exception:
        return False


def create_access_token(
    subject: str,
    claims: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Issue a signed JWT access token for an authenticated user or device session."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if claims:
        payload.update(claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed JWT token, raising UnauthorizedAccessError on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedAccessError("Access token has expired. Please authenticate again.")
    except jwt.InvalidTokenError:
        raise UnauthorizedAccessError("Invalid authentication token signature or format.")

