import json, os
BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.normpath(os.path.join(BASE, "..", "config.json"))

def _load():
    try:
        with open(CFG, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def _save(d):
    os.makedirs(os.path.dirname(CFG), exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)

_cfg = _load()
FS_BEARER = _cfg.get("FS_BEARER", "")
FS_HOST = _cfg.get("FS_HOST", "")

def set_fs_bearer(v: str):
    global FS_BEARER; FS_BEARER = v or ""
    d = _load(); d["FS_BEARER"] = FS_BEARER; _save(d)

def set_fs_host(v: str):
    global FS_HOST; FS_HOST = v or ""
    d = _load(); d["FS_HOST"] = FS_HOST; _save(d)
