APP_QSS = """
* { font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; }
QMainWindow { background: #f6f7fb; }
QSplitter::handle { background: transparent; }
QGroupBox { border: 1px solid #e8e8ee; border-radius: 14px; margin-top: 10px; padding: 12px; background: #fff; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #5b5f6a; font-weight: 700; }
QLabel[hint="true"] { color: #6b7280; }
QTabWidget::pane { border: 0; }
QTabBar::tab { background: #fff; padding: 9px 16px; border: 1px solid #e8e8ee; border-bottom: 2px solid transparent; margin-right: 6px; border-top-left-radius: 10px; border-top-right-radius: 10px; }
QTabBar::tab:selected { border-bottom: 2px solid #7c3aed; }
QTableWidget { background: #fff; border: 1px solid #e8e8ee; border-radius: 12px; gridline-color: #ececf3; alternate-background-color: #fafafa; }
QTableWidget::item:selected { background: #ede9fe; }
QHeaderView::section { background: #f6f3ff; color: #2b2f38; padding: 9px 10px; border: 1px solid #ececf3; font-weight: 800; }
QPushButton { background: #7c3aed; color: #fff; border: 0; border-radius: 12px; padding: 10px 18px; font-weight: 800; }
QPushButton:hover { background: #6d28d9; }
QPushButton:disabled { background: #d1d5db; color: #6b7280; }
QLineEdit, QComboBox { background: #fff; border: 1px solid #e8e8ee; border-radius: 10px; padding: 8px 10px; }
QListWidget#Sidebar { background: #ffffff; border-right: 1px solid #e8e8ee; outline: none; }
QListWidget#Sidebar::item { margin: 10px 8px; border-radius: 14px; padding: 14px 8px; font-size: 20px; }
QListWidget#Sidebar::item:selected { background: #ede9fe; color: #4c1d95; }
QCalendarWidget QWidget { alternate-background-color: #faf9ff; }
QCalendarWidget QToolButton { background: transparent; color: #111827; font-weight: 800; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #c7c9d1; border-radius: 5px; min-height: 40px; }
"""
