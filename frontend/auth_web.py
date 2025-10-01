from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineProfile, QWebEnginePage
from PyQt5.QtWebEngineWidgets import QWebEngineView
from utils import db

API_HOST = "mapi.itstep.org"

class _AuthInterceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        host = info.requestUrl().host()
        if API_HOST in host:
            headers = info.requestHeaders()
            auth = bytes(headers.get(b"Authorization", b"")).decode("utf-8")
            if auth.lower().startswith("bearer "):
                token = auth.split(" ", 1)[1].strip()
                if token:
                    db.set_mystat_token(token)
                    
class LoginWebDialog(QDialog):
    def __init__(self, city: str = "aqtobe", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вход в MyStat")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.resize(480, 640)

        lay = QVBoxLayout(self)
        self.view = QWebEngineView(self)
        lay.addWidget(self.view)

        prof = QWebEngineProfile("mystat-login", self)
        prof.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        prof.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        prof.setHttpCacheMaximumSize(50 * 1024 * 1024)

        interceptor = _AuthInterceptor()
        try:
            prof.setUrlRequestInterceptor(interceptor)
        except AttributeError:
            prof.setRequestInterceptor(interceptor)

        page = QWebEnginePage(prof, self.view)
        self.view.setPage(page)
        self.view.load(QUrl("https://mystat.itstep.org/login"))

        self.view.urlChanged.connect(self._maybe_close)

    def _maybe_close(self, _):
        tok = db.get_mystat_token()
        if tok:
            QMessageBox.information(self, "MyStat", "Авторизация выполнена.")
            self.accept()
