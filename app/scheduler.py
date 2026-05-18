import json
import time
from datetime import datetime

from app.config import CHECK_INTERVAL_SECONDS, PRODUCTS_FILE, REQUEST_DELAY_SECONDS
from app.crawler import get_price
from app.notifier import send_discord_message
from app.storage import get_last_price, save_to_csv


def load_products():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def check_product(item):
    name = item["name"]
    url = item["url"]
    target_price = item["target_price"]

    current_price = get_price(url)
    last_price = get_last_price(name)

    if current_price is None:
        print(f"[{name}] price not found.")
        return

    if current_price == last_price:
        print(f"[{name}] no change ({current_price} KRW)")
        return

    save_to_csv(name, current_price)

    if current_price <= target_price:
        message = (
            f"[Target reached] {name}\n"
            f"Current price: {current_price} KRW / Target: {target_price} KRW"
        )
    else:
        message = f"[Price changed] {name}: {last_price} -> {current_price} KRW"

    send_discord_message(message)


def run_monitor():
    products = load_products()

    while True:
        print(f"\n--- {datetime.now().strftime('%H:%M:%S')} price check started ---")

        for item in products:
            try:
                check_product(item)
            except Exception as error:
                print(f"[{item.get('name', 'unknown')}] monitoring failed: {error}")

            time.sleep(REQUEST_DELAY_SECONDS)

        print(f"\n--- price check finished. Waiting {CHECK_INTERVAL_SECONDS} seconds. ---")
        time.sleep(CHECK_INTERVAL_SECONDS)
