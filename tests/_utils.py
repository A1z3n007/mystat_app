import json, os
def load_token():
    token = os.environ.get("MYSTAT_TOKEN")
    if token:
        return token.strip()
    cfg = "config.json"
    if os.path.exists(cfg):
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                return json.load(f).get("token","").strip()
        except Exception:
            pass
    raise SystemExit("Нет токена. Задай env MYSTAT_TOKEN или config.json")
