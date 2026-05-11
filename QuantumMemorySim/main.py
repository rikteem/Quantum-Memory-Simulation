"""
Quantum Memory Simulator — entry point.

Run from the project root:
    python main.py

Requirements:  see requirements.txt
"""

import sys
import os

# Ensure the project root is on sys.path so all subpackages resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from gui.main_window import MainWindow


def main():
    # Enable high-DPI scaling on Windows
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Quantum Memory Simulator")
    app.setStyle("Fusion")

    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    win = MainWindow()
    win.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
