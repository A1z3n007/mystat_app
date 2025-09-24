from tests._utils import load_token
from backend.mystat_api import get_homeworks
def main():
    t = load_token()
    items, meta = get_homeworks(t, status=3, limit=1000, sort="-hw.time"), {}
    if isinstance(items, tuple):
        items, meta = items
    cnt = len(items)
    print("HW_NOT_DONE:", cnt, "meta:", meta)
    raise SystemExit(0 if cnt >= 0 else 1)
if __name__ == "__main__":
    main()