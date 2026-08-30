import argparse
from typing import Iterable
from faker import Faker
from app.database import get_connection

DEFAULT_USER_COUNT = 100_000

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate fake users and insert them into the database."
    )
    parser.add_argument(
        "count",
        nargs="?",
        type=int,
        default=None,
        help="Number of users to generate (default: 100000)",
    )
    parser.add_argument(
        "--count",
        dest="count_flag",
        type=int,
        default=None,
        help="Number of users to generate via named argument.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Rows inserted per batch (default: 5000).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate user payloads without writing to the database.",
    )
    return parser


def resolve_count(args: argparse.Namespace) -> int:
    count = args.count_flag if args.count_flag is not None else args.count
    if count is None:
        count = DEFAULT_USER_COUNT
    if count <= 0:
        raise ValueError("count must be greater than 0")
    return count


def generate_user_rows(fake: Faker, count: int) -> list[tuple[int, str, int, str, bool]]:
    rows: list[tuple[int, str, int, str, bool]] = []
    for user_id in range(1, count + 1):
        name = fake.name()
        age = fake.random_int(min=18, max=80)
        email = f"{fake.email().split('@', 1)[0]}_{user_id}@{fake.email().split('@', 1)[1]}"
        is_male = fake.boolean()
        rows.append((user_id, name, age, email, is_male))
    return rows


def insert_users(rows: Iterable[tuple[int, str, int, str, bool]], batch_size: int) -> None:
    insert_sql = """
        INSERT INTO users (id, name, age, email, is_male)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name,
            age = EXCLUDED.age,
            email = EXCLUDED.email,
            is_male = EXCLUDED.is_male
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            batch: list[tuple[int, str, int, str, bool]] = []
            for row in rows:
                batch.append(row)
                if len(batch) >= batch_size:
                    cursor.executemany(insert_sql, batch)
                    batch.clear()
            if batch:
                cursor.executemany(insert_sql, batch)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        count = resolve_count(args)
    except ValueError as exc:
        parser.error(str(exc))

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than 0")

    fake = Faker()
    rows = generate_user_rows(fake, count)

    if args.dry_run:
        print(f"Dry run: generated {len(rows)} user records without saving to the database.")
        return

    insert_users(rows, args.batch_size)
    print(f"Inserted/updated {len(rows)} users into the database.")


if __name__ == "__main__":
    main()
