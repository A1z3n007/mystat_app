import os, sqlite3, threading

_DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")
_LOCK = threading.Lock()

def _conn():
    c = sqlite3.connect(_DB_PATH)
    c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
    return c

def _get(k, default=""):
    with _LOCK:
        c = _conn()
        try:
            row = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
            return row[0] if row else default
        finally:
            c.close()

def _set(k, v):
    with _LOCK:
        c = _conn()
        try:
            c.execute(
                "INSERT INTO kv(k,v) VALUES(?,?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (k, v or "")
            )
            c.commit()
        finally:
            c.close()

def get_mystat_token() -> str: return _get("mystat_token", "")
def set_mystat_token(v: str):   _set("mystat_token", v or "")

def get_city() -> str:          return _get("mystat_city", "aqtobe")
def set_city(v: str):           _set("mystat_city", (v or "aqtobe").lower())

def get_fs_bearer():   return _get("fs_bearer", "")
def set_fs_bearer(v):  _set("fs_bearer", v or "")

def get_fs_directory(): return _get("fs_directory", "")
def set_fs_directory(v): _set("fs_directory", v or "")

def get_fs_host():     return _get("fs_host", "")
def set_fs_host(v):    _set("fs_host", v or "")
