from app.products_config import load_products
from app.storage import count_products, list_products, sync_products_from_config


def seed_products_from_config_if_empty():
    if count_products(include_inactive=True) > 0:
        return 0

    products = load_products()
    sync_products_from_config(products)
    return len(products)


def load_active_products():
    seed_products_from_config_if_empty()
    return list_products()
