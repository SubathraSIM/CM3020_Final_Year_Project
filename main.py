import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.database.database import create_database
from src.ui.main_window import MainWindow
from src.ui.translations import prepare_translations


PROJECT_ROOT = Path(__file__).resolve().parent
STYLE_PATH = PROJECT_ROOT / "src" / "ui" / "styles.css"


def load_stylesheet():
    return STYLE_PATH.read_text(encoding="utf-8")


def main():
    create_database()

    # All UI modules have been imported through MainWindow,
    # so all English interface strings are registered now.
    prepare_translations()

    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())