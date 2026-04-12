"""Rate limiting setup — slowapi.

Key function: uses user_id from JWT when available, falls back to client IP.
"""

import os

from fastapi import Request
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_user_or_ip(request: Request) -> str:
    """Extract user_id from JWT for per-user rate limiting, else use IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            token = auth.removeprefix("Bearer ")
            secret = os.getenv("JWT_SECRET", "")
            if secret:
                payload = jwt.decode(token, secret, algorithms=["HS256"])
                return f"user:{payload['sub']}"
        except (JWTError, KeyError):
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_get_user_or_ip)
