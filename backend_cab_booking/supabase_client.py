"""
Supabase client singleton.

Uses the *service role* key so the backend can bypass Row Level Security — every table in
icabbi_taxi_schema.sql is written/read through this. The service role key must only ever
live server-side (this process's .env); never send it to a browser, mobile app, or any
client-side code.

supabase-py's client is synchronous under the hood (it wraps httpx's sync client), so
booking_db.py wraps every call in asyncio.to_thread() to keep it off the pipeline's event
loop — this module just builds and caches the client itself.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from loguru import logger
from supabase import Client, create_client

load_dotenv(override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


@lru_cache(maxsize=1)
def get_supabase() -> Client | None:
    """Returns a cached Supabase client, or None if SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
    aren't set — callers should treat None as "database unavailable" and fail the tool call
    gracefully rather than crashing the pipeline."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in .env — "
            "booking_db calls will fail until these are configured."
        )
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
