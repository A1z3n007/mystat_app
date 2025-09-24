import os, tempfile
from tests._utils import load_token
from backend.mystat_api import get_homeworks, upload_to_fs, homework_create

def main():
    t = load_token()
    directory = os.environ.get("MYSTAT_FS_DIR", "").strip() or None
    items_meta = get_homeworks(t, status=3, limit=1, sort="-hw.time")
    items = items_meta[0] if isinstance(items_meta, tuple) else items_meta
    if not items:
        print("Нет ДЗ для отправки")
        raise SystemExit(0)
    hw_id = int(items[0]["id"])
    with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".zip") as f:
        f.write(b"PK\x03\x04demo zip body")  # заглушка
        tmp = f.name
    try:
        url = upload_to_fs(t, tmp, directory=directory)
        res = homework_create(t, hw_id, url, "Задание выполнено!")
        ok = bool(res)
        print("UPLOADED:", url)
        print("CREATE_RES:", res)
        raise SystemExit(0 if ok else 1)
    finally:
        try: os.remove(tmp)
        except Exception: pass

if __name__ == "__main__":
    main()
