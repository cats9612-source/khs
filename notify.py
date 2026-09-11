import json
import os
import sys

import requests

DATA_FILE = os.getenv("OUTPUT_FILE", "availability.json")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not BOT_TOKEN or not CHAT_ID:
    print("Telegram secrets are missing.", file=sys.stderr)
    raise SystemExit(2)

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

times = ", ".join(data.get("times") or []) or "time slot detected"
message = (
    "🚨 Maguro Mart reservation available\n\n"
    f"Date: {data['target_date']}\n"
    f"Party: {data['party_size']} people\n"
    f"Available: {times}\n\n"
    f"{data['url']}\n\n"
    "Availability can disappear quickly. Open TableCheck and book manually."
)

r = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    },
    timeout=20,
)
r.raise_for_status()
print("Telegram notification sent.")
