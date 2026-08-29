import os
import psycopg

def get_connection():
    return psycopg.connect(
        os.getenv(
            "DATABASE_URL",
            "postgresql://app_user:app_password@localhost:5432/app_db",
        )
    )
