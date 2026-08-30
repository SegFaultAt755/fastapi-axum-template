"""FastAPI endpoints for user lookup and hash benchmark operations."""

from typing import Any

from fastapi import FastAPI, HTTPException, Path, Query
from psycopg.rows import dict_row

from app.database import get_connection
from app.workload import DEFAULT_ITERATIONS, MAX_ITERATIONS, compute_digest

app = FastAPI()


def fetch_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Load a user row by its primary key."""
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, name, age, email, is_male
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            return cursor.fetchone()


def build_compute_response(
    digest: str, iterations: int, user_id: int | None = None
) -> dict[str, Any]:
    """Build a consistent payload for compute results."""
    payload: dict[str, Any] = {
        "digest": digest,
        "iterations": iterations,
    }
    if user_id is not None:
        payload["user_id"] = user_id
    return payload


def build_user_payload(user: dict[str, Any]) -> str:
    """Flatten a user record into the benchmark input string."""
    fields = ("id", "name", "age", "email", "is_male")
    return "|".join(str(user[field]) for field in fields)


@app.get("/")
def read_root() -> str:
    """Simple health endpoint used during local verification."""
    return "Hello, World!"


@app.get("/user/{user_id}")
def get_user(user_id: int) -> dict[str, Any]:
    """Fetch a single user by id."""
    user = fetch_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/user/{user_id}/age/{age}")
def update_user_age(user_id: int, age: int = Path(ge=0, le=150)) -> dict[str, Any]:
    """Update a user's age and return the refreshed record."""
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE users
                SET age = %s
                WHERE id = %s
                RETURNING id, name, age, email, is_male
                """,
                (age, user_id),
            )
            user = cursor.fetchone()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.get("/compute")
def compute_without_database(
    data: str = "benchmark-payload",
    iterations: int = Query(DEFAULT_ITERATIONS, ge=1, le=MAX_ITERATIONS),
) -> dict[str, Any]:
    """Benchmark hash work without touching the database."""
    return build_compute_response(compute_digest(data, iterations), iterations)


@app.get("/compute-db/{user_id}")
def compute_with_database(
    user_id: int,
    iterations: int = Query(DEFAULT_ITERATIONS, ge=1, le=MAX_ITERATIONS),
) -> dict[str, Any]:
    """Benchmark hash work using a user record from the database."""
    user = fetch_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    data = build_user_payload(user)
    return build_compute_response(compute_digest(data, iterations), iterations, user_id)
