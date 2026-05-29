import json
import os
from urllib.parse import urlparse

from app.config import PRODUCTS_FILE


def load_products():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_products(products):
    temp_path = f"{PRODUCTS_FILE}.tmp"

    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(products, file, ensure_ascii=False, indent=4)
        file.write("\n")

    os.replace(temp_path, PRODUCTS_FILE)


def validate_product(name, url, target_price):
    name = name.strip()
    url = url.strip()

    if not name:
        raise ValueError("Product name is required.")

    parsed_url = urlparse(url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("Product URL must start with http:// or https://.")

    try:
        target_price = int(str(target_price).replace(",", "").strip())
    except ValueError as error:
        raise ValueError("Target price must be a number.") from error

    if target_price <= 0:
        raise ValueError("Target price must be greater than 0.")

    return {
        "name": name,
        "url": url,
        "target_price": target_price,
    }


def add_product_to_config(name, url, target_price):
    products = load_products()
    product = validate_product(name, url, target_price)

    if find_product_index(products, product["name"]) is not None:
        raise ValueError("Product name already exists.")

    products.append(product)
    save_products(products)
    return product


def update_product_in_config(old_name, name, url, target_price):
    products = load_products()
    product = validate_product(name, url, target_price)
    product_index = find_product_index(products, old_name)

    if product_index is None:
        raise ValueError("Product was not found in products.json.")

    duplicate_index = find_product_index(products, product["name"])

    if duplicate_index is not None and duplicate_index != product_index:
        raise ValueError("Product name already exists.")

    products[product_index] = product
    save_products(products)
    return product


def remove_product_from_config(name):
    products = load_products()
    product_index = find_product_index(products, name)

    if product_index is None:
        return False

    del products[product_index]
    save_products(products)
    return True


def find_product_index(products, name):
    for index, product in enumerate(products):
        if product["name"] == name:
            return index

    return None
