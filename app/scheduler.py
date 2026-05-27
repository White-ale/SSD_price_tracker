import json
import time
from datetime import datetime

from app.config import CHECK_INTERVAL_SECONDS, PRODUCTS_FILE, REQUEST_DELAY_SECONDS
from app.crawler import get_price
from app.notifier import send_discord_message
from app.storage import (
    get_last_price,
    initialize_database,
    save_price_record,
    upsert_product,
)


def load_products():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def check_product(item):
    name = item["name"]
    url = item["url"]
    target_price = item["target_price"]
    product_id = upsert_product(name, url, target_price)

    current_price = get_price(url)
    last_price = get_last_price(product_id)

    if current_price is None:
        print(f"[{name}] price not found.")
        return

    save_price_record(product_id, name, current_price)

    if current_price == last_price:
        print(f"[{name}] no change ({current_price} KRW)")
        return

    if current_price <= target_price:
        message = (
            f"[Target reached] {name}\n"
            f"Current price: {current_price} KRW / Target: {target_price} KRW"
        )
    else:
        message = f"[Price changed] {name}: {last_price} -> {current_price} KRW"

    send_discord_message(message)


def run_once():
    initialize_database()
    products = load_products()

    print(f"\n--- {datetime.now().strftime('%H:%M:%S')} price check started ---")

    for item in products:
        try:
            check_product(item)
        except Exception as error:
            print(f"[{item.get('name', 'unknown')}] monitoring failed: {error}")

        time.sleep(REQUEST_DELAY_SECONDS)

    print("\n--- price check finished. ---")


def run_monitor():
    while True:
        run_once()
        print(f"\n--- waiting {CHECK_INTERVAL_SECONDS} seconds. ---")
        time.sleep(CHECK_INTERVAL_SECONDS)
