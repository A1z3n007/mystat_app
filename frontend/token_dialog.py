from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton

class TokenDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Введите JWT токен")
        self.token = None

        layout = QVBoxLayout()

        self.label = QLabel("Введите ваш JWT токен от mystat:")
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Normal)

        self.button = QPushButton("Сохранить")
        self.button.clicked.connect(self.save_token)

        layout.addWidget(self.label)
        layout.addWidget(self.input)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def save_token(self):
        self.token = self.input.text().strip()
        self.accept()
