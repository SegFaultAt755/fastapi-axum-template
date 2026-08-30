from fastapi import FastAPI, HTTPException, Path, Query
from psycopg.rows import dict_row
from app.database import get_connection
from app.workload import DEFAULT_ITERATIONS, MAX_ITERATIONS, compute_digest

app = FastAPI()

@app.get("/")
def read_root():
    return "Hello, World!"

@app.get("/user/{user_id}")
def get_user(user_id: int):
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
            user = cursor.fetchone()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.put("/user/{user_id}/age/{age}")
def update_user_age(user_id: int, age: int = Path(ge=0, le=150)):
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
):
    return {
        "digest": compute_digest(data, iterations),
        "iterations": iterations,
    }


@app.get("/compute-db/{user_id}")
def compute_with_database(
    user_id: int,
    iterations: int = Query(DEFAULT_ITERATIONS, ge=1, le=MAX_ITERATIONS),
):
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
            user = cursor.fetchone()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    data = "|".join(str(user[field]) for field in ("id", "name", "age", "email", "is_male"))
    return {
        "digest": compute_digest(data, iterations),
        "iterations": iterations,
        "user_id": user_id,
    }
