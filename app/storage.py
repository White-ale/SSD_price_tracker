import sqlite3
from datetime import datetime

from app.config import DATABASE_FILE


def get_connection():
    return sqlite3.connect(DATABASE_FILE)


def rows_to_dicts(cursor, rows):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


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
                created_at TEXT NOT NULL
            )
            """
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

        connection.commit()


def upsert_product(name, url, target_price):
    # Keep products.json and the products table in sync by product name.
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO products (name, url, target_price, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                url = excluded.url,
                target_price = excluded.target_price
            """,
            (name, url, target_price, now),
        )
        connection.commit()

        cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
        return cursor.fetchone()[0]


def save_price_record(product_id, name, price):
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            WHERE id = ?
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
                COUNT(price_records.id) AS record_count
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

    return summaries
