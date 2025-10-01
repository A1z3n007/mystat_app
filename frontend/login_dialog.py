from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QWidget, QMessageBox
)

from utils.icons import qicon_from_url, ICON_URLS
from utils import db
from backend.mystat_api import login_with_credentials

PRIMARY = "#6C59F5"

class LoginDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Вход в MyStat")
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(420, 520)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowIcon(QIcon(qicon_from_url(ICON_URLS["favicon"])))

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(qicon_from_url(ICON_URLS["favicon"]).pixmap(80, 80))
        logo.setAlignment(Qt.AlignCenter)

        htitle = QLabel("MyStat Desktop")
        htitle.setAlignment(Qt.AlignCenter)
        htitle.setObjectName("title")

        subt = QLabel("Введите данные от учётной записи")
        subt.setAlignment(Qt.AlignCenter)
        subt.setObjectName("subtitle")

        self.cb_city = QComboBox()
        self.cb_city.addItems(["aqtobe", "almaty", "astana", "shymkent"])
        saved_city = db.get_city() or "aqtobe"
        i = self.cb_city.findText(saved_city)
        if i >= 0:
            self.cb_city.setCurrentIndex(i)

        self.ed_login = QLineEdit()
        self.ed_login.setPlaceholderText("Логин / Email")

        self.ed_pass = QLineEdit()
        self.ed_pass.setPlaceholderText("Пароль")
        self.ed_pass.setEchoMode(QLineEdit.Password)

        self.btn_eye = QPushButton()
        self.btn_eye.setIcon(qicon_from_url("https://cdn-icons-png.flaticon.com/512/565/565655.png"))
        self.btn_eye.setCheckable(True)
        self.btn_eye.setCursor(Qt.PointingHandCursor)
        self.btn_eye.setFixedWidth(36)
        self.btn_eye.clicked.connect(self._toggle_echo)

        pass_row = QHBoxLayout()
        pass_row.setContentsMargins(0, 0, 0, 0)
        pass_row.addWidget(self.ed_pass, 1)
        pass_row.addWidget(self.btn_eye)

        self.chk_remember = QCheckBox("Запомнить меня")
        self.chk_remember.setChecked(True)

        self.lbl_err = QLabel("")
        self.lbl_err.setObjectName("error")
        self.lbl_err.setWordWrap(True)
        self.lbl_err.setVisible(False)

        self.btn_login = QPushButton("Войти")
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self._do_login)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(self.btn_login)

        root.addWidget(logo)
        root.addWidget(htitle)
        root.addWidget(subt)
        root.addSpacing(8)
        root.addWidget(QLabel("Филиал"))
        root.addWidget(self.cb_city)
        root.addWidget(QLabel("Логин / Email"))
        root.addWidget(self.ed_login)
        root.addWidget(QLabel("Пароль"))
        root.addLayout(pass_row)
        root.addWidget(self.chk_remember)
        root.addSpacing(8)
        root.addWidget(self.lbl_err)
        root.addStretch(1)
        root.addLayout(buttons)

        self.setStyleSheet(f"""
        QLabel#title    {{ font-size: 22px; font-weight: 700; }}
        QLabel#subtitle {{ color: #666; }}
        QLabel#error    {{ color: #EC4845; background: #FFE8E8; padding: 6px 8px; border-radius: 8px; }}
        QLineEdit {{
            padding: 10px 12px; border: 1px solid #E2E2E2; border-radius: 10px;
            background: white; selection-background-color:{PRIMARY};
        }}
        QLineEdit:focus {{ border: 1px solid {PRIMARY}; }}
        QComboBox {{
            padding: 10px 12px; border: 1px solid #E2E2E2; border-radius: 10px; background: white;
        }}
        QPushButton {{
            border-radius: 10px; padding: 10px 16px; background: #F1F2F7; border: none;
        }}
        QPushButton:default, QPushButton#primary {{
            background: {PRIMARY}; color: white; font-weight: 600;
        }}
        """)

        self.ed_login.installEventFilter(self)
        self.ed_pass.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress and ev.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._do_login()
            return True
        return super().eventFilter(obj, ev)

    def _toggle_echo(self):
        if self.btn_eye.isChecked():
            self.ed_pass.setEchoMode(QLineEdit.Normal)
            self.btn_eye.setIcon(qicon_from_url("https://cdn-icons-png.flaticon.com/512/709/709612.png"))
        else:
            self.ed_pass.setEchoMode(QLineEdit.Password)
            self.btn_eye.setIcon(qicon_from_url("https://cdn-icons-png.flaticon.com/512/565/565655.png"))

    def _set_busy(self, busy: bool):
        for w in (self.cb_city, self.ed_login, self.ed_pass, self.btn_eye, self.chk_remember):
            w.setEnabled(not busy)
        self.btn_login.setEnabled(not busy)
        self.setCursor(Qt.BusyCursor if busy else Qt.ArrowCursor)
        self.btn_login.setText("Входим…" if busy else "Войти")

    def _do_login(self):
        city = self.cb_city.currentText().strip()
        login = self.ed_login.text().strip()
        pwd   = self.ed_pass.text().strip()

        if not login or not pwd:
            self._show_err("Заполни логин и пароль.")
            return

        self._set_busy(True)
        try:
            token = login_with_credentials(city, login, pwd)
            if isinstance(token, dict):
                token = token.get("token") or token.get("access_token")

            if not token or not isinstance(token, str):
                raise RuntimeError("Сервер не вернул токен.")

            db.set_mystat_token(token)
            if self.chk_remember.isChecked():
                db.set_city(city)

            self.accept()
        except Exception as e:
            self._show_err(str(e) or "Ошибка входа")
        finally:
            self._set_busy(False)

    def _show_err(self, msg: str):
        self.lbl_err.setText(msg)
        self.lbl_err.setVisible(True)
