# main.py
import sys, json, os
from PyQt5.QtWidgets import QApplication
from frontend.main_window import MainWindow
from frontend.login_dialog import LoginDialog
from backend.mystat_api import login_with_credentials
from frontend.theme import APP_QSS

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_token():
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("token")
        except Exception:
            pass
    return None

def save_token(token: str):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"token": token}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)

    token = load_token()
    if not token:
        dlg = LoginDialog()
        if dlg.exec_() == dlg.Accepted:
            email, password = dlg.get_values()
            try:
                token = login_with_credentials(email, password)
            except Exception as e:
                from PyQt5.QtWidgets import QInputDialog, QMessageBox
                QMessageBox.warning(None, "Логин не удался", f"{e}\n\nМожно вставить готовый Bearer-токен вручную.")
                raw, ok = QInputDialog.getText(None, "Вставьте Bearer-токен", "eyJ0eXAiOiJKV1Qi...:")
                if not ok or not raw:
                    return
                token = raw.strip().replace("Bearer ", "")
            save_token(token)
        else:
            return

    w = MainWindow(token)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
