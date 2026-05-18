import csv
import os
from datetime import datetime

from app.config import BASE_DIR


def get_product_csv_path(name):
    return os.path.join(BASE_DIR, f"{name}.csv")


def save_to_csv(name, price):
    file_path = get_product_csv_path(name)
    file_exists = os.path.exists(file_path)

    with open(file_path, mode="a", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["Date", "Price"])

        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), price])

    print(f"[{name}] saved: {price} KRW")


def get_last_price(name):
    file_path = get_product_csv_path(name)

    if not os.path.exists(file_path):
        return 0

    try:
        with open(file_path, mode="r", encoding="utf-8-sig") as file:
            rows = list(csv.reader(file))

        if len(rows) <= 1:
            return 0

        return int(rows[-1][1])
    except Exception as error:
        print(f"[{name}] failed to read previous price: {error}")
        return 0
