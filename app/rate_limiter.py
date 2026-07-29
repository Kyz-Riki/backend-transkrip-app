"""Rate limiting configuration for the application.

Guest (tanpa login): 5 request/jam berdasarkan IP address
User login: 10 request/jam berdasarkan user_id
"""

import logging
from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from app.services.supabase_client import get_user_from_token

logger = logging.getLogger("uvicorn.error")

# Rate limit constants
GUEST_LIMIT = "5/hour"
USER_LIMIT = "10/hour"


def _get_rate_limit_key(request: Request) -> str:
    """Determine the rate limit key based on authentication status.

    - User login (token valid) → key = "user:{user_id}" (limit terpisah per user)
    - Guest (tanpa token) → key = IP address
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = get_user_from_token(token)
        if user:
            return f"user:{user.id}"

    # Fallback ke IP address untuk guest
    return request.client.host if request.client else "unknown"


def is_guest(request: Request) -> bool:
    """Return True if the request is from a guest (no valid token)."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = get_user_from_token(token)
        if user:
            return False
    return True

def is_logged_in(request: Request) -> bool:
    """Return True if the request is from a logged-in user."""
    return not is_guest(request)


# Inisialisasi limiter dengan key function
limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[],  # Tidak ada default limit global — hanya per-endpoint
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler untuk response 429 yang informatif."""
    # Cek apakah request dari user login atau guest
    auth_header = request.headers.get("authorization", "")
    is_logged_in = False
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = get_user_from_token(token)
        is_logged_in = user is not None

    if is_logged_in:
        message = (
            "Batas penggunaan tercapai: Anda telah mencapai limit 10 request per jam. "
            "Silakan coba lagi nanti."
        )
    else:
        message = (
            "Batas penggunaan tercapai: Guest dibatasi 5 request per jam. "
            "Silakan login untuk mendapatkan kuota lebih besar (10 request/jam)."
        )

    return JSONResponse(
        status_code=429,
        content={"detail": message},
    )
