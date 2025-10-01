from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QWidget, QGroupBox, QHBoxLayout, QSizePolicy,
    QTableWidget, QTableWidgetItem, QPushButton, QSpacerItem, QFileDialog,
    QMessageBox, QStackedWidget, QListWidget, QListWidgetItem, QFrame, QApplication,
    QInputDialog, QTabWidget, QMenu, QAction, QCalendarWidget, QSplitter, QTableWidgetItem, QListView,
    QToolButton, QLineEdit, QDialog, QTextEdit, QScrollArea, QGridLayout
)
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, QUrl, QDate, QSize, pyqtSignal
from PyQt5.QtGui import QDesktopServices

import os
from datetime import date, datetime as dt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from utils import config
from backend.mystat_api import (
    get_user_info, get_attendance, get_progress, get_leader_table, get_activity,
    get_schedule, get_reviews, get_homeworks,
    download_homework_file,
    upload_to_fs,
    homework_create,
    delete_homework,
    _guess_fs_base_from_examples,
    ensure_fs_credentials
)
from frontend.fs_sniffer import open_fs_sniffer
from utils.db import get_fs_directory, set_fs_directory
from utils.icons import qicon_from_url, ICON_URLS
ROLE_STUD_ID = Qt.UserRole + 1

def _make_badge(title: str, value_text: str, bg: str) -> QWidget:
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(2)

    v = QLabel(value_text); v.setObjectName("value"); v.setAlignment(Qt.AlignLeft)
    t = QLabel(title); t.setObjectName("title"); t.setAlignment(Qt.AlignLeft)

    layout.addWidget(v); layout.addWidget(t)

    w.setStyleSheet(f"""
        QWidget {{ background: {bg}; border-radius: 12px; }}
        QLabel#value {{ font-size: 20px; font-weight: 600; }}
        QLabel#title {{ color: #444; }}
    """)
    return w

def _metric(self, title: str, value_text: str):
    w = QWidget()
    lay = QVBoxLayout(w); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(2)
    t = QLabel(title); t.setObjectName("QLabelTitle")
    v = QLabel(value_text); v.setObjectName("QLabelValue")
    lay.addWidget(v); lay.addWidget(t)
    w.setStyleSheet("""
        QWidget { background:#fff; border:1px solid #ececf2; border-radius:12px; }
        QLabel#QLabelValue { font-size:28px; font-weight:700; color:#18181b; }
        QLabel#QLabelTitle { color:#75777c; }
    """)
    return w

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=2.4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()

    def plot_progress(self, x_labels, y_values, title="Прогресс за год"):
        self.ax.clear()
        self.ax.plot(y_values, marker="o")
        self.ax.set_title(title)
        self.ax.set_ylabel("Баллы")
        self.ax.set_xticks(range(len(x_labels)))
        self.ax.set_xticklabels(x_labels, rotation=45, ha="right")
        self.ax.grid(True, axis="y", linestyle="--", alpha=0.3)
        self.draw()
        
class HomeworkDialog(QDialog):
    def __init__(self, parent, token, hw_id, title):
        super().__init__(parent)
        self.token = token
        self.hw_id = hw_id
        self.setWindowTitle(title)
        self.resize(520, 420)
        v = QVBoxLayout(self)
        self.lbl_deadline = QLabel("")
        self.txt = QTextEdit()
        self.btn_file = QPushButton("Выбрать файл…")
        self.btn_send = QPushButton("Отправить")
        v.addWidget(self.lbl_deadline)
        v.addWidget(self.txt, 1)
        h = QHBoxLayout()
        h.addWidget(self.btn_file)
        h.addStretch(1)
        h.addWidget(self.btn_send)
        v.addLayout(h)
        self._chosen = ""
        self.btn_file.clicked.connect(self._pick)
        self.btn_send.clicked.connect(self._send)
        hist = self.hw.get("communication_history") if hasattr(self, "hw") else None
        if hist:
            box = QGroupBox("Отправленные сообщения"); lv = QVBoxLayout(box)
            for item in hist:
                row = QLabel(f"• {item.get('date') or ''} — {item.get('comment') or ''}")
                row.setWordWrap(True); lv.addWidget(row)
            v.addWidget(box)

    def _pick(self):
        p, _ = QFileDialog.getOpenFileName(self, "Файл решения")
        if p:
            self._chosen = p
            self.btn_file.setText(os.path.basename(p))

    def _send(self):
        if not self._chosen:
            QMessageBox.warning(self, "Внимание", "Выберите файл.")
            return
        try:
            link = upload_to_fs(self.token, self._chosen)
            homework_create(self.token, self.hw_id, link, self.txt.toPlainText().strip())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

class HomeworkCard(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, hw: dict, index: int):
        super().__init__()
        self.hw = hw
        self.index = index
        self.setObjectName("HwCard")
        self.setProperty("selected", False)
        self.setFrameShape(QFrame.NoFrame)

        title = hw.get("name_spec", "Задание")
        theme = hw.get("theme", "")
        deadline = (hw.get("completion_time") or "").strip()

        title_lbl = QLabel(title)
        title_lbl.setObjectName("HwTitle")

        sub_lbl = QLabel(theme)
        sub_lbl.setObjectName("HwSub")

        meta = QLabel(("Дедлайн: " + deadline) if deadline else "Без дедлайна")
        meta.setObjectName("HwMeta")

        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)
        v.addWidget(title_lbl)
        v.addWidget(sub_lbl)
        v.addWidget(meta)

    def mousePressEvent(self, e):
        self.clicked.emit(self.index)
        super().mousePressEvent(e)

    def setSelected(self, on: bool):
        self.setProperty("selected", bool(on))
        self.style().unpolish(self)
        self.style().polish(self)



class MainWindow(QMainWindow):
    def __init__(self, token: str):
        super().__init__()
        self.setWindowTitle("MyStat Desktop App")
        self.setWindowIcon(QIcon(qicon_from_url(ICON_URLS["favicon"])))
        self.resize(1200, 720)
        self.token = token
        self.fs_directory = "uYjjAT9ZRiNrBHX3vTdEWMWiboZBKK9v"
        self.fs_bearer = config.FS_BEARER


        wrapper = QWidget(); root = QHBoxLayout(wrapper); root.setContentsMargins(8,8,8,8); root.setSpacing(8)

        self.nav = QWidget()
        nav = QVBoxLayout(self.nav)
        nav.setContentsMargins(8, 8, 8, 8)
        nav.setSpacing(10)

        def _nav_btn(icon_path, tip, index=None, on_click=None):
            b = QToolButton()
            b.setObjectName("Nav")
            b.setIcon(QIcon(icon_path))
            b.setIconSize(QSize(26, 26))
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setToolTip(tip)
            if on_click is not None:
                b.clicked.connect(on_click)
            elif index is not None:
                b.clicked.connect(lambda: self.pages.setCurrentIndex(index))
            nav.addWidget(b, 0, Qt.AlignHCenter)
            return b

        btn_home  = _nav_btn(qicon_from_url(ICON_URLS["home"]), "Главная", 0)
        btn_hw    = _nav_btn(qicon_from_url(ICON_URLS["homework"]), "Домашние задания", 1)
        btn_cal   = _nav_btn(qicon_from_url(ICON_URLS["calendar"]), "Расписание", 2)
        btn_rev   = _nav_btn(qicon_from_url(ICON_URLS["reviews"]), "Отзывы", 3)

        self.nav_btn_fs = _nav_btn(qicon_from_url(ICON_URLS["key"]),"FS (обновить доступ)", None, on_click=self._refresh_fs_access)

        nav.addStretch(1)
        btn_home.setChecked(True)
        
        self.hw_tables = {}
        self.hw_cards = {}
        self.hw_card_list = {}
        self.hw_items_by_status: dict[int, list] = {}
        self.hw_card_widgets: dict[int, list] = {}
        self.hw_selected_idx: dict[int, int] = {1:-1, 2:-1, 3:-1}
        self.hw_cards_layout: dict[int, QVBoxLayout] = {}

        self.pages = QStackedWidget()
        self.page_dash = self._build_tab_dashboard()
        self.page_hw   = self._build_tab_homeworks()
        self.page_sched= self._build_tab_schedule()
        self.page_reviews = self._build_tab_reviews()

        self.pages.addWidget(self.page_dash)
        self.pages.addWidget(self.page_hw)
        self.pages.addWidget(self.page_sched)
        self.pages.addWidget(self.page_reviews)
        self.pages.addWidget(QWidget())

        root.addWidget(self.nav)
        root.addWidget(self.pages, 1)
        self.setCentralWidget(wrapper)
        
        self.setStyleSheet("""
        QToolButton#Nav { width:44px; height:44px; border-radius:12px; }
        QToolButton#Nav::menu-indicator { image: none; }
        QToolButton#Nav:hover { background: rgba(120,99,255,.12); }
        QToolButton#Nav:checked { background:#7863ff; color:white; }
        """)
        self.setStyleSheet(self.styleSheet() + """
        #HwCard { background: #fff; border-radius: 14px; border:1px solid #ececf3; }
        #HwCard:hover { border-color:#d6d6f6; box-shadow: 0 6px 18px rgba(0,0,0,.06); }
        #HwCard[selected="true"] { border-color:#7863ff; box-shadow: 0 10px 26px rgba(120,99,255,.22); }
        #HwCard QLabel#HwTitle { font-weight: 600; font-size: 15px; color:#14151b; }
        #HwCard QLabel#HwSub   { color:#63646d; }
        #HwCard QLabel#HwMeta  { color:#8b8d98; }
        """)
        self.setStyleSheet(self.styleSheet() + """
        #Card { background:#fff; border:1px solid #ececf3; border-radius:14px; }
        #Card QGroupBox::title { subcontrol-origin: margin; left:12px; padding:0 4px; }
        #CardTitle { font-weight:600; font-size:15px; color:#14151b; }
        #Muted { color:#8b8d98; }
        #Tile { border-radius:16px; padding:18px 20px; }
        #Tile QLabel#big   { font-size:32px; font-weight:800; }
        #Tile QLabel#small { color:#E9E8FF; }
        #Tile[accent="violet"] { background:#6C59F5; color:white; }
        #Tile[accent="orange"] { background:#FF6D3D; color:white; }
        #Row { padding:10px 12px; border-radius:10px; }
        #Row:hover { background:#f6f7fb; }
        #Chip { background:#EFF2FF; color:#3F47C6; border-radius:999px; padding:2px 8px; font-size:12px; }
        QTableWidget#Leaders QHeaderView::section { background:transparent; border:none; color:#8b8d98; }
        QTableWidget#Leaders { border:none; }
        """)

    def _mk_tile(self, big_text: str, small_text: str, accent: str) -> QWidget:
        w = QFrame(); w.setObjectName("Tile"); w.setProperty("accent", accent)
        v = QVBoxLayout(w); v.setContentsMargins(20,16,20,16); v.setSpacing(6)
        t_big = QLabel(big_text); t_big.setObjectName("big")
        t_small = QLabel(small_text); t_small.setObjectName("small")
        v.addWidget(t_big); v.addWidget(t_small); v.addStretch(1)
        w.style().unpolish(w); w.style().polish(w)  # применить dynamic property
        return w

    def _mk_card(self, title: str, body: QWidget) -> QFrame:
        card = QFrame(); card.setObjectName("Card")
        lay = QVBoxLayout(card); lay.setContentsMargins(12,10,12,12); lay.setSpacing(8)
        lbl = QLabel(title); lbl.setObjectName("CardTitle")
        lay.addWidget(lbl); lay.addWidget(body)
        return card

    def _mk_row(self, left: str, right: str = "") -> QWidget:
        row = QFrame(); row.setObjectName("Row")
        h = QHBoxLayout(row); h.setContentsMargins(10,6,10,6)
        l = QLabel(left); r = QLabel(right); r.setObjectName("Muted")
        h.addWidget(l); h.addStretch(1); h.addWidget(r)
        return row

    def _build_tab_dashboard(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        user = get_user_info(self.token)
        name = user.get("name") or (
            f"{user.get('user_storage', {}).get('firstname','')} "
            f"{user.get('user_storage', {}).get('lastname','')}"
        ).strip() or "Неизвестно"
        email = user.get("email", "Неизвестно")

        title_lbl = QLabel(f"Имя: {name}"); title_lbl.setStyleSheet("font-weight: 600;")
        email_lbl = QLabel(f"Email: {email}")
        root.addWidget(title_lbl); root.addWidget(email_lbl)

        att = get_attendance(self.token, "month")
        p_attend = att.get("percentOfAttendance", 0)
        p_absent = att.get("percentOfAbsent", 0)
        p_late   = att.get("percentOfLate", 0)

        grp_att = QGroupBox("Посещаемость за 30 дней"); grp_att_l = QVBoxLayout(grp_att)
        badges = QHBoxLayout(); badges.setSpacing(10)
        badges.addWidget(_make_badge("Посещение", f"{p_attend}%", "#EAF8EE"))
        badges.addWidget(_make_badge("Пропуск",   f"{p_absent}%", "#FFF1E8"))
        badges.addWidget(_make_badge("Опоздания", f"{p_late}%",   "#F3F4F6"))
        grp_att_l.addLayout(badges)

        grp_att_l.addWidget(QLabel("Последние занятия:"))
        data = att.get("data", {})
        if data:
            years = sorted(map(int, data.keys()))
            last_year = str(years[-1])
            months_map = data.get(last_year, {})
            if months_map:
                months = sorted(map(int, months_map.keys())); last_month = str(months[-1])
                days_map = months_map.get(last_month, {})
                day_items = sorted(
                    ((int(d), info) for d, info in days_map.items()
                     if info.get("was") and isinstance(info.get("was"), list)),
                    key=lambda x: x[0]
                )
                recent = day_items[-5:] if day_items else []
                for day_num, info in recent:
                    was_list = info.get("was", [])
                    status = "—"; color = "#999"
                    if "1" in was_list: status, color = "✅ Был", "#1A7F37"
                    elif "0" in was_list: status, color = "❌ Пропустил", "#C62828"
                    lbl = QLabel(f"{day_num}: {status}"); lbl.setStyleSheet(f"color: {color};")
                    grp_att_l.addWidget(lbl)
            else:
                grp_att_l.addWidget(QLabel("Нет данных за месяц."))
        else:
            grp_att_l.addWidget(QLabel("Нет данных посещаемости."))
        root.addWidget(grp_att)

        progress = get_progress(self.token, "year")
        from collections import defaultdict, OrderedDict
        sum_by_month = defaultdict(int)
        for dataset in progress.get("data", []):
            for cm in dataset.get("chart_models", []):
                d = cm.get("date"); pts = cm.get("points")
                if pts is not None and d:
                    sum_by_month[d] += pts

        def _mm_yy(s):
            try: return f"{s[5:7]}/{s[2:4]}"
            except Exception: return s

        ordered = OrderedDict(sorted(sum_by_month.items(), key=lambda kv: kv[0]))
        x_labels = [_mm_yy(d) for d in ordered.keys()]
        y_values = list(ordered.values())

        grp_prog = QGroupBox("Годовой прогресс (сумма баллов по месяцам)")
        grp_prog_l = QVBoxLayout(grp_prog)
        canvas = PlotCanvas(self, width=6.2, height=2.6, dpi=100)
        canvas.plot_progress(x_labels, y_values)
        grp_prog_l.addWidget(canvas)
        root.addWidget(grp_prog)

        root.addWidget(self._build_leaderboard_box())

        self.activity_page = 1
        grp_act = QGroupBox("Начисления (последние события)"); act_layout = QVBoxLayout(grp_act)
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["Дата", "Дисциплина", "Действие", "Награда", "Оценка"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setSelectionBehavior(self.tbl.SelectRows)
        self.tbl.setEditTriggers(self.tbl.NoEditTriggers)
        act_layout.addWidget(self.tbl)
        pager = QHBoxLayout()
        self.btn_prev = QPushButton("← Назад"); self.btn_next = QPushButton("Вперёд →")
        self.lbl_page = QLabel(f"Стр. {self.activity_page}")
        self.btn_prev.clicked.connect(self._prev_page); self.btn_next.clicked.connect(self._next_page)
        pager.addWidget(self.btn_prev); pager.addWidget(self.lbl_page); pager.addWidget(self.btn_next)
        pager.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        act_layout.addLayout(pager)
        root.addWidget(grp_act)
        self._load_activity()

        return page
    
    def _make_medal(self, pos: int) -> str:
        return {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, f"{pos}")

    def _fill_leader_table(self, tbl, rows):
        tbl.setRowCount(0)
        for i, x in enumerate(rows):
            tbl.insertRow(i)
            name   = x.get("fio_stud", "-")
            amount = x.get("amount", 0)
            pos    = int(x.get("position", i+1))
            cur    = bool(x.get("current"))

            it_name = QTableWidgetItem(name)
            it_pts  = QTableWidgetItem(str(amount))
            it_pos  = QTableWidgetItem(self._make_medal(pos))

            it_pts.setTextAlignment(Qt.AlignCenter)
            it_pos.setTextAlignment(Qt.AlignCenter)

            if cur:
                it_name.setBackground(Qt.white)
                it_pts.setBackground(Qt.white)
                it_pos.setBackground(Qt.white)
                it_name.setData(Qt.ForegroundRole, None)
                it_name.setForeground(Qt.black)
                font = it_name.font(); font.setBold(True)
                it_name.setFont(font); it_pts.setFont(font); it_pos.setFont(font)

            tbl.setItem(i, 0, it_name)
            tbl.setItem(i, 1, it_pts)
            tbl.setItem(i, 2, it_pos)

        tbl.resizeColumnsToContents()

    def _build_leaderboard_box(self) -> QGroupBox:
        grp = QGroupBox("🏆 Таблица лидеров")
        v = QVBoxLayout(grp)

        tabs = QTabWidget()
        w_group = QWidget(); vg = QVBoxLayout(w_group)
        tbl_g = QTableWidget(0, 3)
        tbl_g.setHorizontalHeaderLabels(["ФИО", "Баллы", "Место"])
        tbl_g.horizontalHeader().setStretchLastSection(True)
        tbl_g.setSelectionBehavior(tbl_g.SelectRows)
        tbl_g.setEditTriggers(tbl_g.NoEditTriggers)
        vg.addWidget(tbl_g)
        tabs.addTab(w_group, "В группе")

        w_stream = QWidget(); vs = QVBoxLayout(w_stream)
        tbl_s = QTableWidget(0, 3)
        tbl_s.setHorizontalHeaderLabels(["ФИО", "Баллы", "Место"])
        tbl_s.horizontalHeader().setStretchLastSection(True)
        tbl_s.setSelectionBehavior(tbl_s.SelectRows)
        tbl_s.setEditTriggers(tbl_s.NoEditTriggers)
        vs.addWidget(tbl_s)
        tabs.addTab(w_stream, "В потоке")

        v.addWidget(tabs)

        try:
            data = get_leader_table(self.token)
        except Exception as e:
            data = {}
            print("leader-table error:", e)

        self._fill_leader_table(tbl_g, data.get("group",{}).get("top",[]) or [])
        self._fill_leader_table(tbl_s, data.get("stream",{}).get("top",[]) or [])

        return grp


    def _build_tab_homeworks(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        hdr = QHBoxLayout()
        self.lbl_hw_title = QLabel("Домашние задания")
        self.lbl_hw_title.setStyleSheet("font-weight: 600;")
        btn_refresh = QPushButton("Обновить")
        hdr.addWidget(self.lbl_hw_title)
        hdr.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        hdr.addWidget(btn_refresh)
        root.addLayout(hdr)

        self.hw_tabs = QTabWidget()
        self.hw_tabs.setDocumentMode(True)
        self.hw_tabs.setTabsClosable(False)

        self.hw_statuses = [(3, "К выполнению"), (2, "На проверке"), (1, "Выполнены")]

        for st, title in self.hw_statuses:
            tab = QWidget()
            v = QVBoxLayout(tab)

            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            content = QWidget()
            lay = QVBoxLayout(content)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(10)
            scroll.setWidget(content)
            v.addWidget(scroll, 1)

            tbl = QTableWidget(0, 7)
            tbl.setHorizontalHeaderLabels(["ID","Создано","Предмет","Тема","Преподаватель","Дедлайн","Файл задания"])
            tbl.setVisible(False)
            v.addWidget(tbl)

            self.hw_tabs.addTab(tab, title)

            self.hw_tables[st] = tbl
            self.hw_cards_layout[st] = lay
            self.hw_card_widgets[st] = []
            self.hw_items_by_status[st] = []
            self.hw_selected_idx[st] = -1

        root.addWidget(self.hw_tabs)

        btns = QHBoxLayout()
        self.btn_hw_open = QPushButton("Открыть задачу…")
        self.btn_hw_download = QPushButton("Скачать файл задания")
        self.btn_hw_upload   = QPushButton("Отправить решение…")
        self.btn_hw_remove   = QPushButton("Удалить решение…")
        btns.addWidget(self.btn_hw_open)
        btns.addWidget(self.btn_hw_download)
        btns.addWidget(self.btn_hw_upload)
        btns.addWidget(self.btn_hw_remove)
        btns.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        root.addLayout(btns)

        btn_refresh.clicked.connect(self._hw_reload_active)
        self.btn_hw_download.clicked.connect(self._hw_download_selected)
        self.btn_hw_upload.clicked.connect(self.on_send_clicked)
        self.btn_hw_remove.clicked.connect(self._hw_remove_selected)
        self.btn_hw_open.clicked.connect(self._open_hw_dialog)
        self.hw_tabs.currentChanged.connect(lambda _: self._hw_reload_active())

        self._hw_reload_active()
        return page

    
    def _render_hw_cards(self, status: int, items: list[dict]) -> None:
        lay = self.hw_cards_layout[status]
        while lay.count():
            it = lay.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)

        self.hw_items_by_status[status] = items or []
        self.hw_card_widgets[status] = []

        for i, hw in enumerate(self.hw_items_by_status[status]):
            card = HomeworkCard(hw, i)
            for c in card.findChildren(QLabel):
                if c.text() == hw.get("name_spec", "Задание"):
                    c.setObjectName("HwTitle")
                elif c.text() == hw.get("theme", ""):
                    c.setObjectName("HwSub")
                else:
                    c.setObjectName("HwMeta")

            card.clicked.connect(lambda idx, st=status: self._on_card_clicked(st, idx))
            lay.addWidget(card)
            self.hw_card_widgets[status].append(card)

        lay.addStretch(1)
        sel = self.hw_selected_idx.get(status, -1)
        if 0 <= sel < len(self.hw_card_widgets[status]):
            self._apply_card_selection(status, sel)

    def _on_card_clicked(self, status: int, index: int) -> None:
        self.hw_selected_idx[status] = index
        self._apply_card_selection(status, index)

        tbl = self.hw_tables[status]
        if 0 <= index < tbl.rowCount():
            tbl.setCurrentCell(index, 0)

    def _apply_card_selection(self, status: int, index: int) -> None:
        for i, w in enumerate(self.hw_card_widgets[status]):
            w.setSelected(i == index)

    def _current_hw_from_cards(self) -> dict | None:
        st = self._active_hw_status()
        idx = self.hw_selected_idx.get(st, -1)
        items = self.hw_items_by_status.get(st, [])
        if 0 <= idx < len(items):
            return items[idx]
        return None

    
    def _open_hw_dialog(self):
        row = self._current_hw_row()
        if row is None:
            return
        hw_id = self._current_hw_id(row)
        title = self.hw_tables[self._active_hw_status()].item(row, 3).text()
        dlg = HomeworkDialog(self, self.token, hw_id, title)
        dlg.exec_()
        self._hw_reload_active()
    
    def _hw_remove_selected(self):
        status, tbl, row = self._hw_selected_row()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Не выбрано ДЗ в текущей вкладке.")
            return
        if status != 2:
            QMessageBox.warning(self, "Внимание", "Удалять можно только во вкладке «На проверке».")
            return
        it = tbl.item(row, 0)
        stud_id = it.data(ROLE_STUD_ID) if it else None
        if not stud_id:
            QMessageBox.warning(self, "Внимание", "Не найден ID отправки (homework_stud.id).")
            return
        confirm = QMessageBox.question(self, "Подтвердите", f"Удалить отправленное решение #{stud_id}?")
        if confirm != QMessageBox.Yes:
            return
        try:
            ok = delete_homework(self.token, int(stud_id))
            if ok:
                QMessageBox.information(self, "Готово", "Решение удалено.")
                self._hw_reload_active()
            else:
                QMessageBox.warning(self, "Внимание", "Сервер вернул false.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"{e}")

    def _hw_status_name(self, st: int) -> str:
        return {3: "К выполнению", 2: "На проверке", 1: "Выполнены",}.get(st, str(st))

    def _hw_fmt_date(self, s: str) -> str:
        if not s or s.startswith("-0001"):
            return "-"
        try:
            return dt.strptime(s[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
        except Exception:
            return s

    def _hw_deadline_color(self, deadline_str: str) -> str:
        try:
            if not deadline_str or deadline_str.startswith("-0001"):
                return ""
            d = dt.strptime(deadline_str[:10], "%Y-%m-%d").date()
            left = (d - date.today()).days
            if left < 0:
                return "#FDE2E2"
            if left <= 2:
                return "#FFF2CC"
            return "#EAF8EE"
        except Exception:
            return ""

    def _hw_reload_active(self):
        idx = self.hw_tabs.currentIndex()
        status = self.hw_statuses[idx][0]
        tbl = self.hw_tables[status]
        self._load_homeworks_into_table(status, tbl)
        self.btn_hw_remove.setEnabled(status == 2)

    def _load_homeworks_into_table(self, status: int, table: QTableWidget):
        try:
            items, meta = get_homeworks(self.token, status=status, limit=1000)
        except Exception as e:
            items, meta = [], {}
            print("Ошибка загрузки ДЗ:", e)

        if status == 3:
            total = meta.get("totalCount", len(items))
            self.lbl_hw_title.setText(f"Невыполненные задачи: {int(total)}")
        else:
            self.lbl_hw_title.setText(self._hw_status_name(status))

        table.setRowCount(0)
        if status == 3:
            self._hw_examples_files = []

        for row, hw in enumerate(items):
            table.insertRow(row)
            if status == 3:
                self._hw_examples_files.append(hw.get("file_path"))

            stud = hw.get("homework_stud") or {}
            stud_id = stud.get("id")

            raw_deadline = hw.get("completion_time") or ""
            values = [
                hw.get("id"),
                self._hw_fmt_date(hw.get("creation_time")),
                hw.get("name_spec", "-"),
                hw.get("theme", "-"),
                hw.get("fio_teach", "-"),
                self._hw_fmt_date(raw_deadline),
                hw.get("file_path") or "-",
            ]

            for col, val in enumerate(values):
                it = QTableWidgetItem(str(val))
                if col not in (3, 6):
                    it.setTextAlignment(Qt.AlignCenter)
                if col == 0:
                    it.setData(ROLE_STUD_ID, stud_id)
                table.setItem(row, col, it)

            color = self._hw_deadline_color(raw_deadline)
            if color:
                table.item(row, 5).setBackground(QColor(color))
        self._render_hw_cards(status, items)
        table.resizeColumnsToContents()

    def _hw_current_table_and_status(self):
        idx = self.hw_tabs.currentIndex()
        status = self.hw_statuses[idx][0]
        tbl = self.hw_tables[status]
        return status, tbl

    def _hw_selected_row(self):
        status, tbl = self._hw_current_table_and_status()
        return status, tbl, tbl.currentRow()

    def _hw_context_menu(self, table, pos):
        row = table.indexAt(pos).row()
        if row < 0: return
        m = QMenu(self)
        act_open = m.addAction("Открыть файл задания в браузере")
        act_copy = m.addAction("Копировать ссылку на файл")
        a = m.exec_(table.viewport().mapToGlobal(pos))
        if a == act_open:
            url = table.item(row, 6).text()
            if url and url != "-":
                import webbrowser; webbrowser.open(url)
        elif a == act_copy:
            url = table.item(row, 6).text()
            if url and url != "-":
                QApplication.clipboard().setText(url)


    def _hw_download_selected(self):
        status, tbl = self._hw_current_table_and_status()
        row = tbl.currentRow()
        if row < 0:
            return
        file_url = tbl.item(row, 6).text().strip()
        if not file_url or file_url == "-":
            return
        save_dir = QFileDialog.getExistingDirectory(self, "Куда сохранить файл задания?")
        if not save_dir:
            return
        try:
            path = download_homework_file(self.token, file_url, save_dir)
            QMessageBox.information(self, "Готово", f"Файл сохранён:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл: {e}")

    def _hw_upload_selected(self):
        row = self._current_hw_row()
        if row is None:
            QMessageBox.warning(self, "Внимание", "Не выбрано ДЗ.")
            return
        hw_id = self._current_hw_id(row)
        if hw_id is None:
            QMessageBox.warning(self, "Внимание", "Не могу прочитать ID задачи.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл решения")
        if not file_path:
            return
        answer_text, ok = QInputDialog.getMultiLineText(self, "Комментарий", "answerText:")
        if not ok:
            return
        try:
            link = upload_to_fs(self.token, file_path)
            res = homework_create(self.token, hw_id, link, (answer_text or "").strip())
            QMessageBox.information(self, "Отправлено", f"Задача #{hw_id} отправлена.")
            self._hw_reload_active()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"{e}")


            
    def _current_hw_table(self):
        st = self._active_hw_status()
        return self.hw_tables.get(st)

    def _current_hw_row(self):
        tbl = self._current_hw_table()
        if not tbl:
            return None
        row = tbl.currentRow()
        return row if row >= 0 else None

    def _current_hw_id(self, row: int):
        tbl = self._current_hw_table()
        if not tbl:
            return None
        it = tbl.item(row, 0)
        if not it:
            return None
        s = it.text().strip()
        return int(s) if s.isdigit() else None

    def _active_hw_status(self):
        idx = self.hw_tabs.currentIndex()
        st, _ = self.hw_statuses[idx]
        return st


    def _build_tab_schedule(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)

        top = QHBoxLayout()
        lbl = QLabel("Расписание")
        lbl.setStyleSheet("font-weight:600;")
        top.addWidget(lbl)
        top.addStretch(1)
        v.addLayout(top)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        v.addWidget(self.calendar)

        self.tbl_schedule = QTableWidget(0, 5)
        self.tbl_schedule.setHorizontalHeaderLabels(["Начало", "Конец", "Предмет", "Аудитория", "Преподаватель"])
        self.tbl_schedule.horizontalHeader().setStretchLastSection(True)
        self.tbl_schedule.setEditTriggers(self.tbl_schedule.NoEditTriggers)
        v.addWidget(self.tbl_schedule)

        def _on_date():
            d = self.calendar.selectedDate()
            s = f"{d.year():04d}-{d.month():02d}-{d.day():02d}"
            self._load_day_schedule(s)

        self.calendar.selectionChanged.connect(_on_date)
        _on_date()
        return page

    def _load_day_schedule(self, date_str: str):
        try:
            data = get_schedule(self.token, date_str).get("data", [])
        except Exception:
            data = []
        self.tbl_schedule.setRowCount(len(data))
        for i, les in enumerate(data):
            start = les.get("time_start","-")
            end = les.get("time_end","-")
            subj = les.get("subject_name","-")
            room = les.get("room","-")
            teacher = les.get("teacher_name","-")
            for c, val in enumerate([start, end, subj, room, teacher]):
                it = QTableWidgetItem(str(val))
                if c in (0,1):
                    it.setTextAlignment(Qt.AlignCenter)
                self.tbl_schedule.setItem(i, c, it)
        self.tbl_schedule.resizeColumnsToContents()
        
    def _build_tab_reviews(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        title = QLabel("Отзывы")
        title.setStyleSheet("font-weight:600;")
        v.addWidget(title)
        self.tbl_reviews = QTableWidget(0, 4)
        self.tbl_reviews.setHorizontalHeaderLabels(["Дата","Предмет","Преподаватель","Отзыв"])
        self.tbl_reviews.horizontalHeader().setStretchLastSection(True)
        self.tbl_reviews.setEditTriggers(self.tbl_reviews.NoEditTriggers)
        v.addWidget(self.tbl_reviews)

        def _load():
            try:
                js = get_reviews(self.token, page=1, mark_as_read=False)
                items = js.get("data", [])
            except Exception:
                items = []
            self.tbl_reviews.setRowCount(len(items))
            for i, it in enumerate(items):
                for c, val in enumerate([
                    it.get("date","-"),
                    it.get("full_spec") or it.get("spec") or "-",
                    it.get("teacher","-"),
                    it.get("message","-"),
                ]):
                    cell = QTableWidgetItem(str(val))
                    if c == 0:
                        cell.setTextAlignment(Qt.AlignCenter)
                    self.tbl_reviews.setItem(i, c, cell)
            self.tbl_reviews.resizeColumnsToContents()

        _load()
        return page

    def _fmt_dt(self, s: str) -> str:
        try:
            dtm = dt.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ")
            return dtm.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return s or "-"

    def _alias_ru(self, alias: str) -> str:
        return {"coins": "монеты", "cristals": "кристаллы", "achivements": "ачивки", "points": "баллы", None: ""}.get(alias, alias or "")

    def _load_activity(self):
        items = get_activity(self.token, page=self.activity_page, per_page=20)
        self.lbl_page.setText(f"Стр. {self.activity_page}")
        self.tbl.setRowCount(len(items))
        for row, it in enumerate(items):
            dtm = self._fmt_dt(it.get("created_at"))
            lesson = it.get("lesson_name") or "-"
            action = it.get("name") or "-"
            award_val = it.get("award_value")
            award_alias = self._alias_ru(it.get("award_alias"))
            award = "-" if award_val is None else f"{award_val} {award_alias}"
            mark = "-" if it.get("mark") is None else str(it.get("mark"))
            for col, val in enumerate([dtm, lesson, action, award, mark]):
                item = QTableWidgetItem(val)
                if col in (0, 4): item.setTextAlignment(Qt.AlignCenter)
                self.tbl.setItem(row, col, item)
        self.tbl.resizeColumnsToContents()

    def _next_page(self):
        self.activity_page += 1
        self._load_activity()

    def _prev_page(self):
        if self.activity_page > 1:
            self.activity_page -= 1
            self._load_activity()
            
    def _refresh_fs_access(self):
        try:
            host, bearer, d = ensure_fs_credentials(self.token)
            QMessageBox.information(self, "FS", f"OK\nhost: {host}\nfolder: {d or '-'}")
        except Exception as e:
            QMessageBox.critical(self, "FS", str(e))

    def on_send_clicked(self) -> None:
        hw = self._current_hw_from_cards()
        if not hw:
            st, tbl = self._hw_current_table_and_status()
            row = tbl.currentRow()
            if row >= 0 and row < len(self.hw_items_by_status.get(st, [])):
                hw = self.hw_items_by_status[st][row]

        if not hw:
            QMessageBox.information(self, "Задание", "Выбери карточку задания (или строку таблицы).")
            return

        self._open_send_dialog(hw)

    def _open_send_dialog(self, hw: dict) -> None:
        hw_id = hw.get("id")
        if not hw_id:
            QMessageBox.warning(self, "Внимание", "Не найден ID задания.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(hw.get("name_spec", "Отправить решение"))
        dlg.resize(520, 420)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(hw.get("theme") or ""))

        txt = QTextEdit()
        txt.setPlaceholderText("Текст ответа (answerText)")
        v.addWidget(txt, 1)

        file_row = QHBoxLayout()
        btn_pick = QPushButton("Выбрать файл…")
        lbl_file = QLabel("Файл не выбран")
        lbl_file.setStyleSheet("color:#666;")
        file_row.addWidget(btn_pick)
        file_row.addWidget(lbl_file, 1)
        v.addLayout(file_row)

        btns = QHBoxLayout()
        btns.addStretch(1)
        btn_send = QPushButton("Отправить")
        btns.addWidget(btn_send)
        v.addLayout(btns)

        chosen = {"path": ""}

        def _pick():
            p, _ = QFileDialog.getOpenFileName(self, "Файл решения")
            if p:
                chosen["path"] = p
                lbl_file.setText(os.path.basename(p))

        def _send():
            if not chosen["path"]:
                QMessageBox.warning(dlg, "Внимание", "Выберите файл.")
                return
            try:
                link = upload_to_fs(self.token, chosen["path"])
                homework_create(self.token, int(hw_id), link, txt.toPlainText().strip())
                QMessageBox.information(self, "Отправлено", f"Задача #{hw_id} отправлена.")
                dlg.accept()
                self._hw_reload_active()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

        btn_pick.clicked.connect(_pick)
        btn_send.clicked.connect(_send)
        dlg.exec_()
