import csv
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import PRODUCTS_FILE
from app.storage import initialize_database, save_price_record_at, upsert_product


def load_products_by_name():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
        products = json.load(file)

    return {product["name"]: product for product in products}


def get_csv_path(product_name):
    archived_path = ROOT_DIR / "archive" / f"{product_name}.csv"
    if archived_path.exists():
        return archived_path

    return ROOT_DIR / f"{product_name}.csv"


def migrate_product(product):
    product_id = upsert_product(
        product["name"],
        product["url"],
        product["target_price"],
    )
    csv_path = get_csv_path(product["name"])

    if not csv_path.exists():
        print(f"[skip] {csv_path.name} not found")
        return 0

    migrated_count = 0

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            checked_at = row["Date"]
            price = int(row["Price"])

            if save_price_record_at(product_id, price, checked_at):
                migrated_count += 1

    print(f"[done] {csv_path.name}: {migrated_count} records migrated")
    return migrated_count


def main():
    initialize_database()
    products_by_name = load_products_by_name()
    total_count = 0

    for product in products_by_name.values():
        total_count += migrate_product(product)

    print(f"Migration finished. Total new records: {total_count}")


if __name__ == "__main__":
    main()
