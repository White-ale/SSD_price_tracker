import sqlite3
from datetime import datetime

from app.config import DATABASE_FILE


def get_connection():
    return sqlite3.connect(DATABASE_FILE)


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
    #DB의 PRODUCTS 테이블에 상품 정보를 저장하거나 업데이트하는 함수. 상품 이름을 기준으로 URL과 목표 가격을 저장하거나 업데이트
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
