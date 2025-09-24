from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вход в MyStat")
        v = QVBoxLayout(self)

        self.ed_email = QLineEdit(); self.ed_email.setPlaceholderText("Логин / Email")
        self.ed_pass  = QLineEdit(); self.ed_pass.setPlaceholderText("Пароль"); self.ed_pass.setEchoMode(QLineEdit.Password)

        v.addWidget(QLabel("Введите логин и пароль от MyStat"))
        v.addWidget(self.ed_email)
        v.addWidget(self.ed_pass)

        h = QHBoxLayout()
        btn_ok = QPushButton("Войти"); btn_cancel = QPushButton("Отмена")
        h.addWidget(btn_ok); h.addWidget(btn_cancel)
        v.addLayout(h)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

    def get_values(self):
        return self.ed_email.text().strip(), self.ed_pass.text().strip()
