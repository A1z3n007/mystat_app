import os
import re
import mimetypes
from typing import Tuple, Dict, Any, List, Optional
from urllib.parse import urlparse
from utils.config import FS_BEARER
from utils import config
from utils.db import get_fs_bearer, set_fs_bearer as db_set_fs_bearer, \
                    get_fs_directory, set_fs_directory as db_set_fs_directory, \
                    get_fs_host, set_fs_host as db_set_fs_host
import requests

BASE_URL = "https://mapi.itstep.org/v1/mystat"
API_BASE = "https://mapi.itstep.org"
CITY = "aqtobe"
FS_UPLOAD_URL = "https://fsx3.itstep.org/api/v1/files"
FS_HOSTS = [
    "https://fsx1.itstep.org/api/v1/files",
    "https://fsx2.itstep.org/api/v1/files",
    "https://fsx3.itstep.org/api/v1/files",
    "https://fsx4.itstep.org/api/v1/files",
    "https://fsx5.itstep.org/api/v1/files",
    "https://fs1.itstep.org/api/v1/files",
    "https://fs2.itstep.org/api/v1/files",
    "https://fs3.itstep.org/api/v1/files",
]
FS_HOST_CANDIDATES = ["fsx3.itstep.org","fsx2.itstep.org","fsx1.itstep.org","fsx4.itstep.org","fsx5.itstep.org"]


def _auth_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
    }

def _raise(r: requests.Response):
    raise Exception(f"Ошибка {r.status_code}: {r.text}")

def _city_or_default(city: Optional[str] = None) -> str:
    if city and city.strip():
        return city.strip().lower()
    try:
        from utils.db import get_city
        c = get_city().strip().lower()
        return c or "aqtobe"
    except Exception:
        return "aqtobe"

def get_user_info(token: str) -> Dict[str, Any]:
    r = requests.post(f"{BASE_URL}/auth/me", headers=_auth_headers(token))
    if r.status_code == 200:
        return r.json()
    _raise(r)

def get_attendance(token: str, period: str = "month", *, city: str = None) -> Dict[str, Any]:
    c = _city_or_default(city)
    r = requests.get(
        f"{BASE_URL}/{c}/statistic/attendance",
        headers=_auth_headers(token),
        params={"period": period},
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    _raise(r)

def get_progress(token: str, period: str = "year", *, city: str = None) -> Dict[str, Any]:
    c = _city_or_default(city)
    r = requests.get(
        f"{BASE_URL}/{c}/statistic/progress",
        headers=_auth_headers(token),
        params={"period": period},
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    _raise(r)

def get_leader_table(token: str, *, city: str = None) -> dict:
    c = _city_or_default(city)
    url = f"{API_BASE}/v1/mystat/{c}/progress/leader-table"
    r = requests.get(url, headers=_auth_headers(token), timeout=30)
    r.raise_for_status()
    return r.json()

def get_activity(token: str, page: int = 1, per_page: int = 20, *, city: str = None) -> List[Dict[str, Any]]:
    c = _city_or_default(city)
    r = requests.get(
        f"{BASE_URL}/{c}/progress/activity",
        headers=_auth_headers(token),
        params={"new_format": 1, "per_page": per_page, "page": page},
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    _raise(r)

def get_schedule(token: str, date_filter: str, *, city: str = None) -> Dict[str, Any]:
    c = _city_or_default(city)
    r = requests.get(
        f"{BASE_URL}/{c}/schedule/get-month",
        headers=_auth_headers(token),
        params={"type": "day", "date_filter": date_filter},
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    _raise(r)

def get_homeworks(token: str, status: int, limit: int = 1000, sort: str = "-hw.time", *, city: str = None):
    c = _city_or_default(city)
    url = f"{API_BASE}/v1/mystat/{c}/homework/list"
    r = requests.get(url, headers=_auth_headers(token), params={"status": status, "limit": limit, "sort": sort}, timeout=30)
    r.raise_for_status()
    js = r.json()
    return js.get("data", []), js.get("_meta", {})

def login_with_credentials(*args, **kwargs) -> str:
    city = kwargs.get("city")
    if len(args) == 2:
        identifier, password = args
    elif len(args) == 3:
        city, identifier, password = args
    else:
        raise TypeError("login_with_credentials(login, password) или login_with_credentials(city, login, password)")

    c = _city_or_default(city)

    ses = requests.Session()
    candidates = [
        (f"{API_BASE}/v1/mystat/auth/login",        "json", {"login": identifier, "password": password}),
        (f"{API_BASE}/v1/mystat/{c}/auth/login",    "json", {"login": identifier, "password": password}),
        (f"{API_BASE}/v1/auth/login",               "json", {"email": identifier, "password": password}),
        (f"{API_BASE}/v1/login",                    "json", {"login": identifier, "password": password}),
        (f"{API_BASE}/v1/mystat/auth/login",        "form", {"login": identifier, "password": password}),
        (f"{API_BASE}/v1/auth/login",               "form", {"email": identifier, "password": password}),
    ]

    def _extract_token_from_json(js):
        for path in [("token",), ("access_token",), ("data","token"), ("data","access_token")]:
            cur, ok = js, True
            for k in path:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    ok = False; break
            if ok and isinstance(cur, str) and cur:
                return cur
        return None

    jwt_re = re.compile(r'^[A-Za-z0-9\-\_]+\.[A-Za-z0-9\-\_]+\.[A-Za-z0-9\-\_]+$')
    errors = []

    for url, mode, payload in candidates:
        try:
            r = ses.post(url, json=payload, timeout=30) if mode == "json" else ses.post(url, data=payload, timeout=30)
        except Exception as e:
            errors.append(f"{url} — exception: {e}")
            continue

        if r.status_code == 200:
            try:
                js = r.json()
                tok = _extract_token_from_json(js)
                if tok:
                    return tok
            except Exception:
                pass
            raw = (r.text or "").strip().strip('"').strip("'")
            if jwt_re.match(raw):
                return raw
            errors.append(f"{url} — 200, но не распознан токен: {r.text[:180]}")
            continue

        try:
            errors.append(f"{url} — HTTP {r.status_code}: {r.text[:200]}")
        except Exception:
            errors.append(f"{url} — HTTP {r.status_code}")

    raise RuntimeError("Login failed. Tried:\n" + "\n".join(errors))


def get_homeworks(token: str, status: int, limit: int = 1000, sort: str = "-hw.time"):
    url = f"{API_BASE}/v1/mystat/{CITY}/homework/list"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"status": status, "limit": limit, "sort": sort}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    js = r.json()
    return js.get("data", []), js.get("_meta", {})


def get_reviews(token: str, page: int = 1, mark_as_read: bool = False) -> dict:
    url = f"{API_BASE}/v1/mystat/{CITY}/reviews/list"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"mark_as_read": "true" if mark_as_read else "false", "page": page}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def _filename_from_cd(cd: str) -> Optional[str]:
    if not cd:
        return None
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, re.IGNORECASE)
    return m.group(1) if m else None


def _ext_from_content_type(ct: str) -> str:
    if not ct:
        return ".zip"
    ext = mimetypes.guess_extension(ct.split(";")[0].strip())
    return ext or (".zip" if ct == "application/octet-stream" else ".bin")


def download_homework_file(token: str, file_url: str, save_dir: str) -> str:
    os.makedirs(save_dir, exist_ok=True)
    headers = {"Authorization": f"Bearer {token}"}
    with requests.get(file_url, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        cd = r.headers.get("content-disposition") or r.headers.get("Content-Disposition") or ""
        ct = r.headers.get("content-type") or r.headers.get("Content-Type") or ""
        fn = _filename_from_cd(cd)
        if not fn or fn.lower() == "attachment" or "." not in fn:
            tail = file_url.rstrip("/").split("/")[-1]
            base = tail if tail and tail != "files" else "attachment"
            ext = _ext_from_content_type(ct)
            if not base.endswith(ext):
                fn = f"{base}{ext}"
            else:
                fn = base
        path = os.path.join(save_dir, fn)
        with open(path, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
    return path


def _try_upload_once(url: str, token: str, file_path: str, with_auth: bool, token_in_query: bool = False) -> str:
    up_url = url
    if token_in_query:
        sep = "&" if "?" in up_url else "?"
        up_url = f"{up_url}{sep}access-token={token}"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://mystat.itstep.org",
        "Referer": "https://mystat.itstep.org/",
        "X-Requested-With": "XMLHttpRequest",
    }
    if with_auth:
        headers["Authorization"] = f"Bearer {token}"

    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        r = requests.post(up_url, headers=headers, files=files, allow_redirects=True, timeout=60)

    if r.status_code not in (200, 201):
        raise Exception(f"HTTP {r.status_code}: {r.text}")

    if "application/json" in r.headers.get("Content-Type", ""):
        data = r.json()
        if isinstance(data, dict):
            if data.get("url"):
                return data["url"]
            for k in ("uuid", "id", "file", "hash"):
                if data.get(k):
                    return re.sub(r"/api/v1/files/?$", f"/api/v1/files/{data[k]}", url)

    m = re.search(r'"(?:uuid|id|file|hash)"\s*:\s*"([A-Za-z0-9_\-]+)"', r.text or "")
    if m:
        return re.sub(r"/api/v1/files/?$", f"/api/v1/files/{m.group(1)}", url)

    raise Exception(f"Не удалось распознать ответ FS: {r.text[:200]}")


def _guess_fs_base_from_examples(examples: List[str]) -> Optional[str]:
    for u in examples:
        if not u:
            continue
        m = re.match(r"https://(fsx?\d\.itstep\.org)/api/v1/files/", u)
        if m:
            return f"https://{m.group(1)}/api/v1/files/"
    return None

def _host_ok(host, bearer):
    try:
        r = requests.options(f"https://{host}/api/v1/files", headers={"Authorization": f"Bearer {bearer}"}, timeout=10)
        return r.status_code in (200, 204)
    except Exception:
        return False

def _pick_fs_host(bearer):
    h = get_fs_host()
    if h and _host_ok(h, bearer):
        return h
    for x in FS_HOST_CANDIDATES:
        if _host_ok(x, bearer):
            db_set_fs_host(x)
            return x
    raise RuntimeError("FS: нет доступного хоста")

def upload_to_fs(token: str, file_path: str, directory: str = "", fs_bearer: str = "", fs_host: str = "") -> str:
    if not fs_bearer or not fs_host:
        host, bearer, auto_dir = ensure_fs_credentials(token)
        fs_host = fs_host or host
        fs_bearer = fs_bearer or bearer
        directory = directory or auto_dir
    url = f"{fs_host}/api/v1/files"
    with open(file_path, "rb") as f:
        files = [("files[]", (os.path.basename(file_path), f, "application/octet-stream"))]
        data = {}
        if directory:
            data["directory"] = directory
        headers = {"Authorization": f"Bearer {fs_bearer}"}
        r = requests.post(url, headers=headers, files=files, data=data, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"FS upload error {r.status_code}: {r.text}")
    js = r.json()
    if isinstance(js, list) and js:
        return js[0].get("link")
    if isinstance(js, dict) and js.get("link"):
        return js.get("link")
    raise RuntimeError(f"FS upload: неожиданный ответ {r.text}")


def homework_create(token: str, homework_id: int, filename_url: str, answer_text: str = ""):
    url = f"{API_BASE}/v1/mystat/{CITY}/homework/create"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "answerText": answer_text or None,
        "filename": filename_url,
        "id": homework_id,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Create failed {r.status_code}: {r.text}")
    try:
        return r.json()
    except Exception:
        return {"status": r.status_code, "text": r.text}

def delete_homework(token: str, stud_homework_id: int) -> bool:
    url = f"{API_BASE}/v1/mystat/{CITY}/homework/delete/{int(stud_homework_id)}"
    r = requests.delete(url, headers=_auth_headers(token), timeout=30)
    if r.status_code in (200, 201, 204):
        try:
            js = r.json()
            if isinstance(js, bool):
                return js
        except Exception:
            pass
        return True
    raise RuntimeError(f"Delete failed {r.status_code}: {r.text}")

def get_user_file_token(token: str) -> dict:
    url = f"{API_BASE}/v1/mystat/{CITY}/user/file-token"
    r = requests.get(url, headers=_auth_headers(token), timeout=20)
    r.raise_for_status()
    return r.json()

def ensure_fs_credentials(token: str):
    host = get_fs_host()
    bearer = get_fs_bearer()
    directory = get_fs_directory()
    if host and bearer and directory:
        return host, bearer, directory
    js = get_user_file_token(token)
    host = (js.get("domain") or "").rstrip("/")
    bearer = js.get("token") or ""
    directory = (js.get("directories") or {}).get("homeworkDirId") or ""
    if not (host and bearer):
        raise RuntimeError("Не удалось получить FS доступ")
    db_set_fs_host(host)
    db_set_fs_bearer(bearer)
    if directory:
        db_set_fs_directory(directory)
    return host, bearer, directory

