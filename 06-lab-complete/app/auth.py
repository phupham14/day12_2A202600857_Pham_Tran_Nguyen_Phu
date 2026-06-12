"""API Key + JWT authentication."""
import time
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)

# Demo users: username → (hashed_password, role)
# In production, store in DB with proper hashing
_USERS = {
    "student": ("demo123", "user"),
    "teacher": ("teach456", "admin"),
}


def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key


def create_token(username: str, password: str) -> dict:
    if username not in _USERS or _USERS[username][0] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    role = _USERS[username][1]
    payload = {
        "sub": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "role": role, "expires_in": 3600}


def verify_token(credentials: HTTPAuthorizationCredentials = Security(_bearer)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(token: dict = Security(verify_token)) -> dict:
    if token.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return token
