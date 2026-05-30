import requests

from app.config import DISCORD_WEBHOOK_URL


def send_discord_message(message):
    if not DISCORD_WEBHOOK_URL:
        print("Discord webhook URL is not configured. Skip notification.")
        return False

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=10,
        )
    except requests.RequestException as error:
        print(f"Discord notification failed: {error}")
        return False

    if response.status_code == 204:
        print("Discord notification sent.")
        return True

    print(f"Discord notification failed: {response.status_code}")
    return False
