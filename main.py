import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from frontend.main_window import MainWindow
from frontend.login_dialog import LoginDialog
from frontend.theme import APP_QSS
from utils import db
from utils.icons import qicon_from_url, ICON_URLS

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MyStat Desktop")
    app.setStyleSheet(APP_QSS or "")
    app.setWindowIcon(qicon_from_url(ICON_URLS["favicon"]))

    token = db.get_mystat_token()
    if not token:
        dlg = LoginDialog()
        if dlg.exec_() != dlg.Accepted:
            sys.exit(0)
        token = db.get_mystat_token()

    w = MainWindow(token)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
