from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from app.database import get_connection

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
