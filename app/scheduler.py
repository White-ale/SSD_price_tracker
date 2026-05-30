import time

from app.config import (
    CHECK_INTERVAL_SECONDS,
    CHECK_RUN_SOURCE,
    FAILURE_ALERT_THRESHOLD,
    MIN_CHECK_INTERVAL_MINUTES,
    MISSING_RUN_ALERT_AFTER_MINUTES,
    MISSING_RUN_ALERT_COOLDOWN_MINUTES,
    REQUEST_DELAY_SECONDS,
)
from app.crawler import get_price
from app.notifier import send_discord_message
from app.product_source import load_active_products
from app.storage import (
    current_timestamp,
    finish_check_run,
    get_last_price,
    get_latest_successful_check_run,
    get_recent_alert_event,
    get_recent_successful_check_run,
    initialize_database,
    minutes_since_timestamp,
    record_skipped_check_run,
    record_product_check_failure,
    record_product_check_success,
    record_alert_event,
    save_price_record,
    start_check_run,
    upsert_product,
)

MISSING_RUN_ALERT_TYPE = "missing_successful_run"
MISSING_RUN_ALERT_KEY = "price-check"


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
    return f"{price} KRW"


def build_price_notification_message(name, current_price, last_price, target_price):
    if last_price == 0:
        if current_price <= target_price:
            return (
                f"[Target reached] {name} {format_krw(current_price)} "
                f"(Target: {format_krw(target_price)})"
            )

        print(f"[{name}] first price saved ({format_krw(current_price)}).")
        return None

    if current_price == last_price:
        print(f"[{name}] no change ({format_krw(current_price)})")
        return None

    target_crossed = last_price > target_price and current_price <= target_price
    if target_crossed:
        return (
            f"[Target reached] {name} {format_krw(current_price)} "
            f"(Target: {format_krw(target_price)})"
        )

    price_delta = current_price - last_price

    if price_delta > 0:
        print(
            f"[{name}] price increased without notification "
            f"({format_krw(last_price)} -> {format_krw(current_price)})."
        )
        return None

    return (
        f"[Price dropped] {name}: {last_price} -> "
        f"{format_krw(current_price)} (-{format_krw(abs(price_delta))})"
    )


def build_missing_run_alert_message(latest_success, minutes_since):
    finished_at = latest_success["finished_at"] or latest_success["started_at"]
    source = latest_success.get("source") or "unknown"

    return (
        "[Tracker warning] No successful price check recently.\n"
        f"Last successful run: #{latest_success['id']} at {finished_at} KST.\n"
        f"Elapsed: {minutes_since} minutes.\n"
        f"Threshold: {MISSING_RUN_ALERT_AFTER_MINUTES} minutes.\n"
        f"Source: {source}."
    )


def send_missing_run_alert_if_needed():
    if MISSING_RUN_ALERT_AFTER_MINUTES <= 0:
        print("[watchdog] missing-run alert is disabled.")
        return False

    latest_success = get_latest_successful_check_run()

    if latest_success is None:
        print("[watchdog] no successful price check has been recorded yet.")
        return False

    finished_at = latest_success["finished_at"] or latest_success["started_at"]
    minutes_since = minutes_since_timestamp(finished_at)

    if minutes_since is None:
        print(f"[watchdog] cannot parse latest success timestamp: {finished_at}")
        return False

    if minutes_since < MISSING_RUN_ALERT_AFTER_MINUTES:
        print(f"[watchdog] latest successful run is {minutes_since} minutes old.")
        return False

    recent_alert = get_recent_alert_event(
        MISSING_RUN_ALERT_TYPE,
        MISSING_RUN_ALERT_KEY,
        MISSING_RUN_ALERT_COOLDOWN_MINUTES,
    )

    if recent_alert is not None:
        print(
            "[watchdog] missing-run alert already sent at "
            f"{recent_alert['sent_at']} KST."
        )
        return False

    message = build_missing_run_alert_message(latest_success, minutes_since)

    if not send_discord_message(message):
        return False

    record_alert_event(
        MISSING_RUN_ALERT_TYPE,
        MISSING_RUN_ALERT_KEY,
        message,
    )
    return True


def run_once():
    initialize_database()
    send_missing_run_alert_if_needed()

    recent_success = get_recent_successful_check_run(MIN_CHECK_INTERVAL_MINUTES)
    if recent_success:
        finished_at = recent_success["finished_at"] or recent_success["started_at"]
        skip_reason = (
            f"Run #{recent_success['id']} already succeeded at {finished_at} KST."
        )
        record_skipped_check_run(CHECK_RUN_SOURCE, skip_reason)
        print(
            "\n--- price check skipped. "
            f"{skip_reason} ---"
        )
        return

    run_id = start_check_run(CHECK_RUN_SOURCE)
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


def run_watchdog():
    initialize_database()
    send_missing_run_alert_if_needed()


def run_monitor():
    while True:
        run_once()
        print(f"\n--- waiting {CHECK_INTERVAL_SECONDS} seconds. ---")
        time.sleep(CHECK_INTERVAL_SECONDS)
