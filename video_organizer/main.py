import sys
from PySide6.QtWidgets import QApplication

from app.ui_main import MainWindow
from app.utils import setup_logging


def main():
    setup_logging()
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
