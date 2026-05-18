import requests

from app.config import DISCORD_WEBHOOK_URL


def send_discord_message(message):
    if not DISCORD_WEBHOOK_URL:
        print("Discord webhook URL is not configured. Skip notification.")
        return

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json={"content": message},
        timeout=10,
    )

    if response.status_code == 204:
        print("Discord notification sent.")
    else:
        print(f"Discord notification failed: {response.status_code}")
