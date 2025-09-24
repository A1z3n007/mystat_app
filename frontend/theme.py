APP_QSS = """
* { font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; }

QMainWindow { background: #f6f7fb; }

QGroupBox {
    border: 1px solid #e8e8ee;
    border-radius: 8px;
    margin-top: 10px;
    padding: 8px;
    background: #fff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px; padding: 0 4px; color: #60636b; font-weight: 600;
}

QLabel[hint="true"] { color: #6b7280; }

QTabWidget::pane { border: 0; }
QTabBar::tab {
    background: #fff; padding: 6px 12px; border: 1px solid #e8e8ee;
    border-bottom: 2px solid transparent; margin-right: 6px; border-top-left-radius: 6px; border-top-right-radius: 6px;
}
QTabBar::tab:selected { border-bottom: 2px solid #7c3aed; }

QTableWidget {
    background: #fff; border: 1px solid #e8e8ee; border-radius: 8px;
    gridline-color: #ececf3;
}
QHeaderView::section {
    background: #faf9ff; color: #374151; padding: 6px; border: 1px solid #ececf3;
    font-weight: 600;
}
QTableWidget::item:selected { background: #ede9fe; }

QPushButton {
    background: #7c3aed; color: white; border: 0; border-radius: 8px; padding: 7px 14px; font-weight: 600;
}
QPushButton:hover { background: #6d28d9; }
QPushButton:disabled { background: #d1d5db; color: #6b7280; }

QListWidget#Sidebar {
    background: #fff; border-right: 1px solid #e8e8ee; padding: 8px; outline: none;
}
QListWidget#Sidebar::item { padding: 10px 12px; margin: 4px 0; border-radius: 8px; }
QListWidget#Sidebar::item:selected { background: #ede9fe; color: #4c1d95; }

QLineEdit, QComboBox {
    background: #fff; border: 1px solid #e8e8ee; border-radius: 8px; padding: 6px 8px;
}
"""
