import os
#config.py는 프로그램이 실행될 때 필요한 경로, 주기, 환경변수, 요청 헤더 같은 설정값을 중앙에서 관리하는 파일이다.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.json")
DATABASE_FILE = os.path.join(BASE_DIR, "price_tracker.db")
CHECK_INTERVAL_SECONDS = 60 * 60
REQUEST_DELAY_SECONDS = 3


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


load_env_file()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
