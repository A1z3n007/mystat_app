from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QWidget, QGroupBox, QHBoxLayout, QSizePolicy,
    QTableWidget, QTableWidgetItem, QPushButton, QSpacerItem, QFileDialog,
    QMessageBox, QStackedWidget, QListWidget, QListWidgetItem, QFrame, QApplication,
    QInputDialog, QTabWidget, QMenu, QAction, QCalendarWidget, QSplitter
)
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, QUrl, QDate
from PyQt5.QtGui import QDesktopServices

import datetime
from datetime import date, datetime as dt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from backend.mystat_api import (
    get_user_info, get_attendance, get_progress, get_leader_table, get_activity,
    get_schedule, get_homeworks,
    download_homework_file,
    upload_to_fs,
    homework_create,
    _guess_fs_base_from_examples,
)


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

class MainWindow(QMainWindow):
    def __init__(self, token: str):
        super().__init__()
        self.setWindowTitle("MyStat Desktop App")
        self.resize(1200, 720)
        self.token = token

        wrapper = QWidget(); root = QHBoxLayout(wrapper); root.setContentsMargins(8,8,8,8); root.setSpacing(8)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.addItem("Главная")
        self.sidebar.addItem("Домашние задания")
        self.sidebar.addItem("Расписание")
        self.sidebar.addItem("Отзывы (скоро)")
        self.sidebar.setFixedWidth(200)

        self.pages = QStackedWidget()

        self.page_dash = self._build_tab_dashboard()
        self.page_hw   = self._build_tab_homeworks()
        self.page_sched= self._build_tab_schedule()

        self.pages.addWidget(self.page_dash)
        self.pages.addWidget(self.page_hw)
        self.pages.addWidget(self.page_sched)
        self.pages.addWidget(QWidget())

        root.addWidget(self.sidebar)
        root.addWidget(self.pages, 1)
        self.setCentralWidget(wrapper)

        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)
        

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

        self.hw_statuses = [(3, "К выполнению"),(2, "На проверке"),(1, "Выполнены")]
        self.hw_tables = {}
        self._hw_examples_files = []

        for st, title in self.hw_statuses:
            tab = QWidget(); v = QVBoxLayout(tab)

            tbl = QTableWidget(0, 7)
            tbl.setHorizontalHeaderLabels(
                ["ID", "Создано", "Предмет", "Тема", "Преподаватель", "Дедлайн", "Файл задания"]
            )
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setSelectionBehavior(tbl.SelectRows)
            tbl.setEditTriggers(tbl.NoEditTriggers)
            tbl.setContextMenuPolicy(Qt.CustomContextMenu)
            tbl.customContextMenuRequested.connect(lambda pos, t=tbl: self._hw_context_menu(t, pos))

            v.addWidget(tbl)
            self.hw_tabs.addTab(tab, title)
            self.hw_tables[st] = tbl

        root.addWidget(self.hw_tabs)

        btns = QHBoxLayout()
        self.btn_hw_download = QPushButton("Скачать файл задания")
        self.btn_hw_upload   = QPushButton("Отправить решение…")
        btns.addWidget(self.btn_hw_download)
        btns.addWidget(self.btn_hw_upload)
        btns.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        root.addLayout(btns)

        btn_refresh.clicked.connect(self._hw_reload_active)
        self.btn_hw_download.clicked.connect(self._hw_download_selected)
        self.btn_hw_upload.clicked.connect(self._hw_upload_selected)
        self.hw_tabs.currentChanged.connect(lambda _: self._hw_reload_active())

        self._hw_reload_active()
        return page

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
                table.setItem(row, col, it)

            color = self._hw_deadline_color(raw_deadline)
            if color:
                table.item(row, 5).setBackground(QColor(color))

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
        st, tbl, row = self._hw_selected_row()
        if row < 0: return
        url = tbl.item(row, 6).text()
        if not url or url == "-": return
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        target_dir = QFileDialog.getExistingDirectory(self, "Куда сохранить?")
        if not target_dir: return
        try:
            path = download_homework_file(self.token, url, target_dir)
            QMessageBox.information(self, "Готово", f"Сохранено:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка загрузки файла", str(e))


    def _hw_upload_selected(self):
        from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox
        row = self._current_hw_row()
        if row is None:
            QMessageBox.warning(self, "Внимание", "Не выбрано ДЗ в текущей вкладке.")
            return

        hw_id = self._current_hw_id(row)
        if hw_id is None:
            QMessageBox.warning(self, "Внимание", "Не могу прочитать ID задачи.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл решения")
        if not file_path:
            return

        if not hasattr(self, "fs_directory"):
            self.fs_directory = None
        if not self.fs_directory:
            text, ok = QInputDialog.getText(self, "Каталог в FS", "directory токен (оставь пусто — корень):")
            if ok:
                self.fs_directory = (text or "").strip()

        try:
            link = upload_to_fs(self.token, file_path, directory=self.fs_directory)
            res = homework_create(self.token, hw_id, link, "Задание выполнено!")
            QMessageBox.information(self, "Отправлено", f"Задача #{hw_id} отправлена.\nФайл: {link}\nОтвет: {res}")
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
        outer = QVBoxLayout(page)

        split = QSplitter()
        outer.addWidget(split)

        left = QWidget(); vl = QVBoxLayout(left)
        cal = QCalendarWidget()
        cal.setGridVisible(True)
        vl.addWidget(QLabel("🗓 Выберите дату"), 0, Qt.AlignLeft)
        vl.addWidget(cal)
        split.addWidget(left)

        right = QWidget(); vr = QVBoxLayout(right)
        grp = QGroupBox("Расписание на день")
        vg = QVBoxLayout(grp)

        tbl = QTableWidget(0, 6)
        tbl.setHorizontalHeaderLabels(["Дата", "Начало", "Конец", "Предмет", "Преподаватель", "Аудитория"])
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setSelectionBehavior(tbl.SelectRows)
        tbl.setEditTriggers(tbl.NoEditTriggers)

        vg.addWidget(tbl)
        vr.addWidget(grp)
        split.addWidget(right)
        split.setSizes([300, 800])

        def load_for(qdate: QDate):
            day = qdate.toString("yyyy-MM-dd")
            try:
                sched = get_schedule(self.token, day)
            except Exception as e:
                print("schedule error:", e)
                sched = {"data": []}
            lessons = sched.get("data", [])
            tbl.setRowCount(0)
            for r, les in enumerate(lessons):
                tbl.insertRow(r)
                values = [
                    les.get("date", day),
                    les.get("time_start", "-"),
                    les.get("time_end", "-"),
                    les.get("subject_name", "-"),
                    les.get("teacher_name", "-"),
                    les.get("room", "-"),
                ]
                for c, val in enumerate(values):
                    it = QTableWidgetItem(str(val))
                    if c in (0,1,2,5):
                        it.setTextAlignment(Qt.AlignCenter)
                    tbl.setItem(r, c, it)
            tbl.resizeColumnsToContents()

        cal.selectionChanged.connect(lambda: load_for(cal.selectedDate()))
        load_for(cal.selectedDate())

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
