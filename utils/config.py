import json
import os

CONFIG_FILE = "config.json"

def load_token():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("token")
    return None

def save_token(token: str):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"token": token}, f)
