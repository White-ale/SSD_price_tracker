import time

from app.config import (
    CHECK_INTERVAL_SECONDS,
    FAILURE_ALERT_THRESHOLD,
    MIN_CHECK_INTERVAL_MINUTES,
    PRICE_CHANGE_ALERT_THRESHOLD_KRW,
    REQUEST_DELAY_SECONDS,
)
from app.crawler import get_price
from app.notifier import send_discord_message
from app.product_source import load_active_products
from app.storage import (
    finish_check_run,
    get_last_price,
    get_recent_successful_check_run,
    initialize_database,
    record_product_check_failure,
    record_product_check_success,
    save_price_record,
    start_check_run,
    upsert_product,
    current_timestamp,
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

    message = build_price_notification_message(
        name,
        current_price,
        last_price,
        target_price,
    )

    if message is None:
        return True

    send_discord_message(message)
    return True


def format_krw(price):
    return f"{price:,} KRW"


def build_price_notification_message(name, current_price, last_price, target_price):
    if last_price == 0:
        if current_price <= target_price:
            return (
                f"[Target reached] {name}\n"
                f"Current price: {format_krw(current_price)} / "
                f"Target: {format_krw(target_price)}\n"
                "First tracked price is already at or below target."
            )

        print(f"[{name}] first price saved ({format_krw(current_price)}).")
        return None

    if current_price == last_price:
        print(f"[{name}] no change ({format_krw(current_price)})")
        return None

    target_crossed = last_price > target_price and current_price <= target_price
    if target_crossed:
        return (
            f"[Target reached] {name}\n"
            f"Previous price: {format_krw(last_price)}\n"
            f"Current price: {format_krw(current_price)} / "
            f"Target: {format_krw(target_price)}"
        )

    price_delta = current_price - last_price
    if abs(price_delta) < PRICE_CHANGE_ALERT_THRESHOLD_KRW:
        print(
            f"[{name}] small change ignored "
            f"({format_krw(last_price)} -> {format_krw(current_price)})."
        )
        return None

    direction = "dropped" if price_delta < 0 else "increased"
    return (
        f"[Price {direction}] {name}\n"
        f"Previous price: {format_krw(last_price)}\n"
        f"Current price: {format_krw(current_price)}\n"
        f"Change: {format_krw(abs(price_delta))}\n"
        f"Target: {format_krw(target_price)}"
    )


def run_once():
    initialize_database()

    recent_success = get_recent_successful_check_run(MIN_CHECK_INTERVAL_MINUTES)
    if recent_success:
        finished_at = recent_success["finished_at"] or recent_success["started_at"]
        print(
            "\n--- price check skipped. "
            f"Run #{recent_success['id']} already succeeded at {finished_at} KST. ---"
        )
        return

    run_id = start_check_run()
    success_count = 0
    failure_count = 0
    run_error = None

    print(f"\n--- {current_timestamp()} KST price check started ---")

    try:
        products = load_active_products()

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
