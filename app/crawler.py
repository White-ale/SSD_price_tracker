import requests
from bs4 import BeautifulSoup

from app.config import HEADERS


def get_price(url):
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    price_tag = soup.select_one(".text__num")

    if price_tag is None:
        return None

    return int(price_tag.text.strip().replace(",", ""))
