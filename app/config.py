import os
#config.py는 프로그램이 실행될 때 필요한 경로, 주기, 환경변수, 요청 헤더 같은 설정값을 중앙에서 관리하는 파일이다.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env_file(path=".env"):
    env_path = os.path.join(BASE_DIR, path)

    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_int_env(name, default):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return int(value)


def get_text_env(name, default=""):
    return os.getenv(name, default).strip().strip('"').strip("'")


load_env_file()

PRODUCTS_FILE = os.path.join(BASE_DIR, "products.json")
DATABASE_FILE = os.path.join(BASE_DIR, "price_tracker.db")
DATABASE_BACKEND = get_text_env(
    "DATABASE_BACKEND",
    "turso" if os.getenv("TURSO_DATABASE_URL") else "sqlite",
).lower()
TURSO_DATABASE_URL = get_text_env("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = get_text_env("TURSO_AUTH_TOKEN")
CHECK_INTERVAL_SECONDS = get_int_env("CHECK_INTERVAL_SECONDS", 60 * 60)
REQUEST_DELAY_SECONDS = get_int_env("REQUEST_DELAY_SECONDS", 3)
MIN_CHECK_INTERVAL_MINUTES = get_int_env("MIN_CHECK_INTERVAL_MINUTES", 0)
FAILURE_ALERT_THRESHOLD = get_int_env("FAILURE_ALERT_THRESHOLD", 3)
API_HOST = get_text_env("API_HOST", "127.0.0.1")
API_PORT = get_int_env("API_PORT", 8000)
DISCORD_WEBHOOK_URL = get_text_env("DISCORD_WEBHOOK_URL")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
