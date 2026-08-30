"""Database connection helpers for the FastAPI service."""

import os

from psycopg_pool import ConnectionPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://app_user:app_password@localhost:5432/app_db",
)
DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))


def _build_pool() -> ConnectionPool:
    """Create the application connection pool once at import time."""
    return ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=DATABASE_POOL_SIZE,
        open=False,
    )


pool = _build_pool()


def get_connection():
    """Return a pooled database connection and open the pool lazily if needed."""
    if pool.closed:
        pool.open(wait=True)
    return pool.connection()
