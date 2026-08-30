import os
from psycopg_pool import ConnectionPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://app_user:app_password@localhost:5432/app_db",
)
DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))
pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=DATABASE_POOL_SIZE,
    open=False,
)

def get_connection():
    if pool.closed:
        pool.open(wait=True)
    return pool.connection()
