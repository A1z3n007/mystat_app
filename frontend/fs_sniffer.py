from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEngineProfile,
    QWebEnginePage,
)

from utils import config


class FsInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, on_found=None, parent=None):
        super().__init__(parent)
        self.on_found = on_found

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        if "api/v1/files" in url and "fs" in url:
            auth = bytes(info.requestHeaders().get(b"Authorization", b"")).decode("utf-8")
            if auth.lower().startswith("bearer "):
                token = auth.split(" ", 1)[1].strip()
                if hasattr(config, "set_fs_bearer"):
                    config.set_fs_bearer(token)
                if self.on_found:
                    self.on_found(token)


def open_fs_sniffer(parent=None):
    view = QWebEngineView(parent)
    view.setAttribute(Qt.WA_DeleteOnClose, True)
    view.setWindowTitle("Открой mystat.itstep.org и отправь любой файл — FS-токен поймается")
    view.resize(1100, 800)

    profile = QWebEngineProfile("fs-sniff", view)
    interceptor = FsInterceptor(lambda tok: QMessageBox.information(view, "FS", "FS токен пойман."))
    try:
        profile.setUrlRequestInterceptor(interceptor)
    except AttributeError:
        profile.setRequestInterceptor(interceptor)

    page = QWebEnginePage(profile, view)
    view.setPage(page)
    view.load(QUrl("https://mystat.itstep.org"))
    view.show()
