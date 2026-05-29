import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from app.config import (
    DATABASE_BACKEND,
    DATABASE_FILE,
    TURSO_AUTH_TOKEN,
    TURSO_DATABASE_URL,
)

KST = timezone(timedelta(hours=9))


def current_timestamp():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def get_connection():
    connection = create_connection()

    try:
        yield connection
    finally:
        connection.close()


def create_connection():
    if DATABASE_BACKEND == "sqlite":
        return sqlite3.connect(DATABASE_FILE, timeout=30)

    if DATABASE_BACKEND == "turso":
        validate_turso_settings()

        try:
            import libsql
        except ImportError as error:
            raise RuntimeError(
                "Turso database requires the libsql package. "
                "Run pip install -r requirements.txt."
            ) from error

        return libsql.connect(
            database=TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN,
        )

    raise RuntimeError(f"Unsupported DATABASE_BACKEND: {DATABASE_BACKEND}")


def validate_turso_settings():
    if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
        raise RuntimeError(
            "Turso database requires TURSO_DATABASE_URL and TURSO_AUTH_TOKEN."
        )

    if TURSO_DATABASE_URL.startswith("TURSO_DATABASE_URL="):
        raise RuntimeError(
            "TURSO_DATABASE_URL must be the URL only, without "
            "the 'TURSO_DATABASE_URL=' prefix."
        )

    if not TURSO_DATABASE_URL.startswith("libsql://"):
        raise RuntimeError("TURSO_DATABASE_URL must start with libsql://.")

    if TURSO_AUTH_TOKEN.startswith("TURSO_AUTH_TOKEN="):
        raise RuntimeError(
            "TURSO_AUTH_TOKEN must be the token only, without "
            "the 'TURSO_AUTH_TOKEN=' prefix."
        )

    if "\n" in TURSO_AUTH_TOKEN or "\r" in TURSO_AUTH_TOKEN:
        raise RuntimeError("TURSO_AUTH_TOKEN must be a single line.")


def rows_to_dicts(cursor, rows):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def ensure_column(cursor, table_name, column_name, column_definition):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def initialize_database():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                target_price INTEGER NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )

        ensure_column(
            cursor,
            "products",
            "is_active",
            "INTEGER NOT NULL DEFAULT 1",
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS price_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                price INTEGER NOT NULL,
                checked_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_price_records_unique
            ON price_records (product_id, checked_at, price)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS check_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                checked_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                failure_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS product_check_status (
                product_id INTEGER PRIMARY KEY,
                last_checked_at TEXT,
                last_success_at TEXT,
                last_failure_at TEXT,
                last_error TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            """
        )

        connection.commit()


def upsert_product(name, url, target_price):
    # Keep products.json and the products table in sync by product name.
    now = current_timestamp()

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO products (name, url, target_price, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                url = excluded.url,
                target_price = excluded.target_price,
                is_active = 1
            """,
            (name, url, target_price, now),
        )
        connection.commit()

        cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
        return cursor.fetchone()[0]


def update_product(product_id, name, url, target_price):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE products
            SET
                name = ?,
                url = ?,
                target_price = ?,
                is_active = 1
            WHERE id = ? AND is_active = 1
            """,
            (name, url, target_price, product_id),
        )
        connection.commit()
        return cursor.rowcount == 1


def deactivate_product(product_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE products
            SET is_active = 0
            WHERE id = ? AND is_active = 1
            """,
            (product_id,),
        )
        connection.commit()
        return cursor.rowcount == 1


def sync_products_from_config(products):
    for product in products:
        upsert_product(
            product["name"],
            product["url"],
            product["target_price"],
        )

    active_names = [product["name"] for product in products]

    with get_connection() as connection:
        cursor = connection.cursor()

        if active_names:
            placeholders = ", ".join("?" for _ in active_names)
            cursor.execute(
                f"""
                UPDATE products
                SET is_active = 0
                WHERE name NOT IN ({placeholders})
                """,
                active_names,
            )
        else:
            cursor.execute("UPDATE products SET is_active = 0")

        connection.commit()


def save_price_record(product_id, name, price):
    checked_at = current_timestamp()
    saved = save_price_record_at(product_id, price, checked_at)

    if saved:
        print(f"[{name}] saved to database: {price} KRW")


def save_price_record_at(product_id, price, checked_at):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO price_records (product_id, price, checked_at)
            VALUES (?, ?, ?)
            """,
            (product_id, price, checked_at),
        )
        connection.commit()
        return cursor.rowcount == 1


def get_last_price(product_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT price
            FROM price_records
            WHERE product_id = ?
            ORDER BY checked_at DESC, id DESC
            LIMIT 1
            """,
            (product_id,),
        )
        row = cursor.fetchone()

    if row is None:
        return 0

    return row[0]


def list_products():
    initialize_database()

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, name, url, target_price, created_at
            FROM products
            WHERE is_active = 1
            ORDER BY id
            """
        )
        return rows_to_dicts(cursor, cursor.fetchall())


def get_product(product_id):
    initialize_database()

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, name, url, target_price, created_at
            FROM products
            WHERE id = ? AND is_active = 1
            """,
            (product_id,),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "url": row[2],
        "target_price": row[3],
        "created_at": row[4],
    }


def get_product_by_name(name, include_inactive=False):
    initialize_database()

    query = """
        SELECT id, name, url, target_price, created_at
        FROM products
        WHERE name = ?
    """
    parameters = [name]

    if not include_inactive:
        query += " AND is_active = 1"

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, parameters)
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "url": row[2],
        "target_price": row[3],
        "created_at": row[4],
    }


def list_price_records(product_id, limit=30):
    initialize_database()

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, product_id, price, checked_at
            FROM price_records
            WHERE product_id = ?
            ORDER BY checked_at DESC, id DESC
            LIMIT ?
            """,
            (product_id, limit),
        )
        return rows_to_dicts(cursor, cursor.fetchall())


def get_price_summary():
    initialize_database()

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                products.id,
                products.name,
                products.url,
                products.target_price,
                latest.price AS latest_price,
                latest.checked_at AS latest_checked_at,
                MIN(price_records.price) AS lowest_price,
                MAX(price_records.price) AS highest_price,
                COUNT(price_records.id) AS record_count,
                product_check_status.last_checked_at AS status_last_checked_at,
                product_check_status.last_success_at AS last_success_at,
                product_check_status.last_failure_at AS last_failure_at,
                product_check_status.last_error AS last_error,
                product_check_status.consecutive_failures AS consecutive_failures
            FROM products
            LEFT JOIN price_records
                ON price_records.product_id = products.id
            LEFT JOIN price_records AS latest
                ON latest.id = (
                    SELECT id
                    FROM price_records
                    WHERE product_id = products.id
                    ORDER BY checked_at DESC, id DESC
                    LIMIT 1
                )
            LEFT JOIN product_check_status
                ON product_check_status.product_id = products.id
            WHERE products.is_active = 1
            GROUP BY products.id
            ORDER BY products.id
            """
        )
        summaries = rows_to_dicts(cursor, cursor.fetchall())

    for summary in summaries:
        latest_price = summary["latest_price"]
        target_price = summary["target_price"]
        summary["is_target_reached"] = (
            latest_price is not None and latest_price <= target_price
        )
        summary["consecutive_failures"] = summary["consecutive_failures"] or 0

    return summaries


def start_check_run():
    now = current_timestamp()

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO check_runs (started_at, status)
            VALUES (?, ?)
            """,
            (now, "running"),
        )
        connection.commit()
        return cursor.lastrowid


def finish_check_run(
    run_id,
    checked_count,
    success_count,
    failure_count,
    error_message=None,
):
    finished_at = current_timestamp()

    if failure_count == 0:
        status = "success"
    elif success_count == 0:
        status = "failed"
    else:
        status = "partial_failure"

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE check_runs
            SET
                finished_at = ?,
                status = ?,
                checked_count = ?,
                success_count = ?,
                failure_count = ?,
                error_message = ?
            WHERE id = ?
            """,
            (
                finished_at,
                status,
                checked_count,
                success_count,
                failure_count,
                error_message,
                run_id,
            ),
        )
        connection.commit()


def record_product_check_success(product_id):
    now = current_timestamp()

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO product_check_status (
                product_id,
                last_checked_at,
                last_success_at,
                consecutive_failures,
                updated_at
            )
            VALUES (?, ?, ?, 0, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                last_checked_at = excluded.last_checked_at,
                last_success_at = excluded.last_success_at,
                last_error = NULL,
                consecutive_failures = 0,
                updated_at = excluded.updated_at
            """,
            (product_id, now, now, now),
        )
        connection.commit()


def record_product_check_failure(product_id, error_message):
    now = current_timestamp()
    error_message = str(error_message)[:500]

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO product_check_status (
                product_id,
                last_checked_at,
                last_failure_at,
                last_error,
                consecutive_failures,
                updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                last_checked_at = excluded.last_checked_at,
                last_failure_at = excluded.last_failure_at,
                last_error = excluded.last_error,
                consecutive_failures = product_check_status.consecutive_failures + 1,
                updated_at = excluded.updated_at
            """,
            (product_id, now, now, error_message, now),
        )
        cursor.execute(
            """
            SELECT consecutive_failures
            FROM product_check_status
            WHERE product_id = ?
            """,
            (product_id,),
        )
        row = cursor.fetchone()
        connection.commit()

    return row[0] if row else 1


def get_latest_check_run():
    initialize_database()

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                id,
                started_at,
                finished_at,
                status,
                checked_count,
                success_count,
                failure_count,
                error_message
            FROM check_runs
            ORDER BY started_at DESC, id DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "started_at": row[1],
        "finished_at": row[2],
        "status": row[3],
        "checked_count": row[4],
        "success_count": row[5],
        "failure_count": row[6],
        "error_message": row[7],
    }
