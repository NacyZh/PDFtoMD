"""Qt stylesheet for the desktop UI."""

APP_STYLESHEET = """
QMainWindow {
    background: #f6f7f9;
}
QGroupBox {
    font-weight: 600;
    border: 1px solid #cfd5dd;
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QTableWidget {
    background: #ffffff;
    border: 1px solid #cfd5dd;
    selection-background-color: #d9e8ff;
}
QPushButton {
    padding: 6px 10px;
}
QProgressBar {
    min-height: 18px;
}
QPlainTextEdit {
    background: #ffffff;
    border: 1px solid #cfd5dd;
}
"""
