import time
from datetime import datetime

from app.config import (
    CHECK_INTERVAL_SECONDS,
    FAILURE_ALERT_THRESHOLD,
    REQUEST_DELAY_SECONDS,
)
from app.crawler import get_price
from app.notifier import send_discord_message
from app.products_config import load_products
from app.storage import (
    finish_check_run,
    get_last_price,
    initialize_database,
    record_product_check_failure,
    record_product_check_success,
    save_price_record,
    start_check_run,
    upsert_product,
)


def check_product(item):
    name = item["name"]
    url = item["url"]
    target_price = item["target_price"]
    product_id = upsert_product(name, url, target_price)

    try:
        current_price = get_price(url)

        if current_price is None:
            raise ValueError("price not found")
    except Exception as error:
        consecutive_failures = record_product_check_failure(product_id, error)
        print(f"[{name}] monitoring failed: {error}")

        if consecutive_failures == FAILURE_ALERT_THRESHOLD:
            send_discord_message(
                f"[Crawler warning] {name}\n"
                f"Failed {consecutive_failures} times in a row.\n"
                f"Last error: {error}"
            )

        return False

    last_price = get_last_price(product_id)
    save_price_record(product_id, name, current_price)
    record_product_check_success(product_id)

    if current_price == last_price:
        print(f"[{name}] no change ({current_price} KRW)")
        return True

    if current_price <= target_price:
        message = (
            f"[Target reached] {name}\n"
            f"Current price: {current_price} KRW / Target: {target_price} KRW"
        )
    else:
        message = f"[Price changed] {name}: {last_price} -> {current_price} KRW"

    send_discord_message(message)
    return True


def run_once():
    initialize_database()
    run_id = start_check_run()
    success_count = 0
    failure_count = 0
    run_error = None

    print(f"\n--- {datetime.now().strftime('%H:%M:%S')} price check started ---")

    try:
        products = load_products()

        for item in products:
            try:
                succeeded = check_product(item)
            except Exception as error:
                print(f"[{item.get('name', 'unknown')}] monitoring failed: {error}")
                failure_count += 1
            else:
                if succeeded:
                    success_count += 1
                else:
                    failure_count += 1

            time.sleep(REQUEST_DELAY_SECONDS)
    except Exception as error:
        run_error = str(error)
        failure_count += 1
        print(f"[run] monitoring failed: {error}")
    finally:
        checked_count = success_count + failure_count
        finish_check_run(
            run_id,
            checked_count,
            success_count,
            failure_count,
            run_error,
        )

    print("\n--- price check finished. ---")


def run_monitor():
    while True:
        run_once()
        print(f"\n--- waiting {CHECK_INTERVAL_SECONDS} seconds. ---")
        time.sleep(CHECK_INTERVAL_SECONDS)
