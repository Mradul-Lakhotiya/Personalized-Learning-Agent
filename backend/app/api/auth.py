"""
auth.py — FastAPI JWT dependency for Supabase authentication.

get_current_user is injected as a Depends() in every protected route.
It verifies the Bearer token via the Supabase Auth API and returns
the authenticated user's UUID.

The Supabase client is created once per process (module-level singleton)
rather than once per request.
"""

import os
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client

security = HTTPBearer()


@lru_cache(maxsize=1)
def _get_supabase_client() -> Client:
    """
    Process-level singleton Supabase client.
    lru_cache ensures this is created once and reused for every request.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL or SUPABASE_SERVICE_KEY is not set. "
            "Check your backend/.env file."
        )
    return create_client(url, key)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    FastAPI dependency. Verifies the Supabase JWT and returns the user UUID.

    Usage:
        @router.get("/protected")
        async def my_route(user_id: str = Depends(get_current_user)):
            ...
    """
    token = credentials.credentials
    supabase = _get_supabase_client()

    try:
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_resp.user.id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
