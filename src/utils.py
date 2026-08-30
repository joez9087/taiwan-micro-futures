import os
import socket
import requests

def get_local_ip():
    """Find local network IP for mobile device access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def send_bark_push(message: str, title: str = "微台指量化晨報", bark_key: str = None) -> bool:
    """
    Bark iOS Push Alert using robust POST JSON API.
    """
    key = bark_key or os.environ.get("BARK_KEY", "")
    if not key:
        return False
        
    url = f"https://api.day.app/{key}"
    payload = {
        "title": title,
        "body": message,
        "sound": "minuet",
        "group": "TaiwanFutures",
        "icon": "https://raw.githubusercontent.com/joez9087/stock-pulse/main/static/taiwan_icon.png"
    }
    try:
        resp = requests.post(url, json=payload, timeout=8)
        return resp.status_code == 200
    except Exception as e:
        print(f"Bark Push Error: {e}")
        return False

def send_line_messaging_api(message: str, channel_access_token: str = None, user_id: str = None) -> bool:
    token = channel_access_token or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    uid = user_id or os.environ.get("LINE_USER_ID", "")
    if not token or not uid:
        return False
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": uid, "messages": [{"type": "text", "text": message}]}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=8)
        return resp.status_code == 200
    except Exception as e:
        print(f"LINE Messaging API Error: {e}")
        return False

def send_discord_webhook(message: str, webhook_url: str = None) -> bool:
    url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return False
    payload = {"content": message}
    try:
        resp = requests.post(url, json=payload, timeout=8)
        return resp.status_code in [200, 204]
    except Exception as e:
        print(f"Discord Webhook Error: {e}")
        return False
