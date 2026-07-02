"""
Sends formatted messages to a Telegram chat via the Bot API.
No external library needed — plain HTTPS POST.
"""
import requests


def send_message(bot_token: str, chat_id: str, text: str, timeout: int = 10) -> bool:
    if not bot_token or not chat_id:
        print("[telegram] Skipped: bot token or chat id not configured.")
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            print(f"[telegram] Failed: {resp.status_code} {resp.text}")
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[telegram] Error: {exc}")
        return False
