import hashlib, os, threading, requests
from PyQt5.QtGui import QIcon, QPixmap

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "_iconcache")
_LOCK = threading.Lock()

def _cache_path(url: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return os.path.join(_CACHE_DIR, f"{h}.ico")

def qicon_from_url(url: str, fallback_path: str = "") -> QIcon:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    path = _cache_path(url)

    if not os.path.isfile(path):
        try:
            r = requests.get(url, timeout=6)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
        except Exception:
            return QIcon(fallback_path) if fallback_path else QIcon()

    pm = QPixmap(path)
    return QIcon(pm)

ICON_URLS = {
    "home":   "https://cdn-icons-png.flaticon.com/512/25/25694.png",
    "homework":  "https://cdn-icons-png.flaticon.com/512/16744/16744420.png",
    "calendar": "https://cdn-icons-png.flaticon.com/512/747/747310.png",
    "key":    "https://cdn-icons-png.flaticon.com/512/10812/10812271.png",
    "cloud":  "https://cdn-icons-png.flaticon.com/512/907/907237.png",
    "reviews":"https://cdn-icons-png.flaticon.com/512/8013/8013078.png",
    "favicon":"https://mystat.itstep.org/favicon.ico"
}
