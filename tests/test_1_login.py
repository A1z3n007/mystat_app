from tests._utils import load_token
from backend.mystat_api import get_user_info
def main():
    t = load_token()
    me = get_user_info(t)
    ok = bool(me and me.get("email"))
    print("USER:", me.get("email"))
    raise SystemExit(0 if ok else 1)
if __name__ == "__main__":
    main()
