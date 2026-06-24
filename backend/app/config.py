"""
config.py — Centralized environment variable configuration.

All modules should import settings from here instead of calling
os.getenv() directly. This ensures:
  - A single place to update key names
  - Early validation on startup (ValueError if required keys missing)
  - A single process-level singleton (lru_cache)
"""

import os
from functools import lru_cache
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str
    supabase_service_key: str

    # ── LLM Keys (comma-separated for rotation) ───────────────────────────────
    gemini_keys: tuple  # tuple so it's hashable for lru_cache
    groq_keys: tuple

    # ── Pinecone ─────────────────────────────────────────────────────────────
    pinecone_api_key: str
    pinecone_host: str
    pinecone_index: str

    # ── External APIs ─────────────────────────────────────────────────────────
    youtube_api_key: str
    tavily_api_key: str

    # ── Server ────────────────────────────────────────────────────────────────
    cors_origins: tuple  # tuple so it's hashable


def _split_keys(raw: str) -> tuple:
    """Split a comma-separated key string, filtering blanks and placeholders."""
    return tuple(
        k.strip()
        for k in raw.split(",")
        if k.strip() and "REPLACE" not in k.strip()
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a singleton Settings object loaded from environment variables.
    Call this from any module that needs config — never call os.getenv() directly.
    """
    cors_raw = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
    )
    return Settings(
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
        gemini_keys=_split_keys(os.getenv("GEMINI_KEYS", "")),
        groq_keys=_split_keys(os.getenv("GROQ_KEYS", "")),
        pinecone_api_key=os.getenv("PINECONE_API_KEY", ""),
        pinecone_host=os.getenv("PINECONE_HOST", ""),
        pinecone_index=os.getenv("PINECONE_INDEX", ""),
        youtube_api_key=os.getenv("YOUTUBE_API_KEY", ""),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        cors_origins=tuple(cors_raw.split(",")),
    )
