import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.database.database import create_database
from src.ui.main_window import MainWindow


PROJECT_ROOT = Path(__file__).resolve().parent

STYLE_PATH = (
    PROJECT_ROOT
    / "src"
    / "ui"
    / "styles.css"
)


def load_stylesheet():
    return STYLE_PATH.read_text(
        encoding="utf-8"
    )


create_database()

app = QApplication(sys.argv)

app.setStyleSheet(
    load_stylesheet()
)

window = MainWindow()
window.show()

sys.exit(app.exec())