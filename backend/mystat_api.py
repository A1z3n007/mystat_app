import os
import re
import mimetypes
from typing import Tuple, Dict, Any, List, Optional
from urllib.parse import urlparse

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


def _auth_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
    }


def _raise(r: requests.Response):
    raise Exception(f"Ошибка {r.status_code}: {r.text}")


def get_user_info(token: str) -> Dict[str, Any]:
    r = requests.post(f"{BASE_URL}/auth/me", headers=_auth_headers(token))
    if r.status_code == 200:
        return r.json()
    _raise(r)


def get_attendance(token: str, period: str = "month") -> Dict[str, Any]:
    r = requests.get(
        f"{BASE_URL}/aqtobe/statistic/attendance",
        headers=_auth_headers(token),
        params={"period": period},
    )
    if r.status_code == 200:
        return r.json()
    _raise(r)


def get_progress(token: str, period: str = "year") -> Dict[str, Any]:
    r = requests.get(
        f"{BASE_URL}/aqtobe/statistic/progress",
        headers=_auth_headers(token),
        params={"period": period},
    )
    if r.status_code == 200:
        return r.json()
    _raise(r)


def get_leader_table(token: str) -> dict:
    url = f"{API_BASE}/v1/mystat/{CITY}/progress/leader-table"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code >= 400:
        raise RuntimeError(f"leader-table {r.status_code}: {r.text}")
    return r.json()



def get_activity(token: str, page: int = 1, per_page: int = 20) -> List[Dict[str, Any]]:
    r = requests.get(
        f"{BASE_URL}/aqtobe/progress/activity",
        headers=_auth_headers(token),
        params={"new_format": 1, "per_page": per_page, "page": page},
    )
    if r.status_code == 200:
        return r.json()
    _raise(r)


def get_schedule(token: str, date_filter: str) -> Dict[str, Any]:
    r = requests.get(
        f"{BASE_URL}/aqtobe/schedule/get-month",
        headers=_auth_headers(token),
        params={"type": "day", "date_filter": date_filter},
    )
    if r.status_code == 200:
        return r.json()
    _raise(r)


def login_with_credentials(identifier: str, password: str) -> str:
    ses = requests.Session()
    candidates = [
        (f"{API_BASE}/v1/mystat/auth/login",        "json", {"login": identifier, "password": password}),
        (f"{API_BASE}/v1/mystat/{CITY}/auth/login", "json", {"login": identifier, "password": password}),
        (f"{API_BASE}/v1/auth/login",               "json", {"email": identifier, "password": password}),
        (f"{API_BASE}/v1/login",                    "json", {"login": identifier, "password": password}),
        (f"{API_BASE}/v1/mystat/auth/login",        "form", {"login": identifier, "password": password}),
        (f"{API_BASE}/v1/auth/login",               "form", {"email": identifier, "password": password}),
    ]

    def _extract_token_from_json(js):
        for path in [("token",), ("access_token",), ("data","token"), ("data","access_token")]:
            cur = js
            ok = True
            for k in path:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    ok = False; break
            if ok and isinstance(cur, str) and cur:
                return cur
        return None

    import re
    jwt_re = re.compile(r'^[A-Za-z0-9\-\_]+\.[A-Za-z0-9\-\_]+\.[A-Za-z0-9\-\_]+$')

    errors = []
    for url, mode, payload in candidates:
        try:
            if mode == "json":
                r = ses.post(url, json=payload, timeout=30)
            else:
                r = ses.post(url, data=payload, timeout=30)
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
        # имя файла
        fname = None
        cd = r.headers.get("content-disposition") or r.headers.get("Content-Disposition")
        if cd and "filename=" in cd:
            fname = cd.split("filename=")[-1].strip('"; ')
        if not fname:
            # вытаскиваем из url
            tail = file_url.rstrip("/").split("/")[-1]
            fname = tail if "." in tail else f"{tail}.zip"
        full = os.path.join(save_dir, fname)
        with open(full, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return full

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


def upload_to_fs(token: str, filepath: str, directory: str | None = None, client_name: str | None = None) -> str:
    import os, requests
    name = client_name or os.path.basename(filepath)
    tried = []
    with open(filepath, "rb") as fh:
        files = {"files[]": (name, fh, "application/octet-stream")}
        data = {}
        if directory:
            data["directory"] = directory
        for base in FS_HOSTS:
            # 1) Authorization header
            try:
                r = requests.post(
                    base,
                    headers={"Authorization": f"Bearer {token}"},
                    data=data,
                    files=files,
                    timeout=90,
                )
                if r.ok:
                    js = r.json()
                    if isinstance(js, list) and js and js[0].get("link"):
                        return js[0]["link"]
                tried.append(f"{base} — HTTP {r.status_code}: {r.text[:180]}")
            except Exception as e:
                tried.append(f"{base} — {e}")

        fh.seek(0)
        files = {"files[]": (name, fh, "application/octet-stream")}
        for base in FS_HOSTS:
            # 2) access-token header
            try:
                r = requests.post(
                    base,
                    headers={"access-token": token},
                    data=data,
                    files=files,
                    timeout=90,
                )
                if r.ok:
                    js = r.json()
                    if isinstance(js, list) and js and js[0].get("link"):
                        return js[0]["link"]
                tried.append(f"{base} header access-token — HTTP {r.status_code}: {r.text[:180]}")
            except Exception as e:
                tried.append(f"{base} header access-token — {e}")

        fh.seek(0)
        files = {"files[]": (name, fh, "application/octet-stream")}
        for base in FS_HOSTS:
            # 3) ?access-token=...
            try:
                r = requests.post(
                    base,
                    params={"access-token": token},
                    data=data,
                    files=files,
                    timeout=90,
                )
                if r.ok:
                    js = r.json()
                    if isinstance(js, list) and js and js[0].get("link"):
                        return js[0]["link"]
                tried.append(f"{base}?access-token= — HTTP {r.status_code}: {r.text[:180]}")
            except Exception as e:
                tried.append(f"{base}?access-token= — {e}")

    raise RuntimeError("FS upload failed. Tried:\n" + "\n".join(tried))

def homework_create(token: str, homework_id: int, filename_url: str, answer_text: str = ""):
    url = f"{API_BASE}/v1/mystat/{CITY}/homework/create"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "answerText": answer_text or None,
        "filename": filename_url,
        "id": homework_id,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Create failed {r.status_code}: {r.text}")
    return r.json()