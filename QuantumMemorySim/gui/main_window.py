"""
Main application window for the Quantum Memory Simulator.

Hosts a QTabWidget with one tab per memory protocol:
  • EIT  — fully implemented
  • AFC  — placeholder (coming soon)
  • GEM  — placeholder (coming soon)
  • Theory — background / equations
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QStatusBar,
    QAction, QMenuBar, QMessageBox, QFileDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

from gui.tabs.eit_tab       import EITTab
from gui.tabs.sweep_tab     import SweepTab
from gui.tabs.theory_tab    import TheoryTab
from gui.tabs.placeholder_tab import PlaceholderTab


APP_TITLE   = "Quantum Memory Simulator"
APP_VERSION = "1.0.0"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE}  v{APP_VERSION}")
        self.setMinimumSize(1100, 720)
        self.resize(1400, 860)

        self._apply_style()
        self._build_menu()
        self._build_tabs()
        self._build_statusbar()

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10pt;
            }
            QTabWidget::pane {
                border: 1px solid #45475a;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #313244;
                color: #a6adc8;
                padding: 8px 18px;
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
                font-size: 10pt;
            }
            QTabBar::tab:selected {
                background: #45475a;
                color: #cba6f7;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #45475a;
                color: #cdd6f4;
            }
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 5px;
                margin-top: 6px;
                padding-top: 6px;
                color: #89b4fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {
                background: #313244;
                border: 1px solid #45475a;
                border-radius: 3px;
                color: #cdd6f4;
                padding: 2px 4px;
            }
            QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton {
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                opacity: 0.85;
            }
            QScrollBar:vertical {
                background: #181825;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #45475a;
                border-radius: 4px;
            }
            QProgressBar {
                background: #313244;
                border: 1px solid #45475a;
                border-radius: 3px;
                text-align: center;
                color: #cdd6f4;
            }
            QProgressBar::chunk {
                background: #89b4fa;
                border-radius: 3px;
            }
            QSplitter::handle {
                background: #45475a;
            }
            QMenuBar {
                background: #181825;
                color: #cdd6f4;
            }
            QMenuBar::item:selected {
                background: #313244;
            }
            QMenu {
                background: #1e1e2e;
                border: 1px solid #45475a;
            }
            QMenu::item:selected {
                background: #313244;
            }
            QStatusBar {
                background: #181825;
                color: #6c7086;
            }
            QLabel {
                color: #cdd6f4;
            }
        """)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self):
        bar = self.menuBar()

        # File
        file_menu = bar.addMenu("File")
        act_quit = QAction("Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Help
        help_menu = bar.addMenu("Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------

    def _build_tabs(self):
        self._tabs = QTabWidget()
        self._tabs.setFont(QFont("Segoe UI", 10))

        self._eit_tab     = EITTab()
        self._sweep_tab   = SweepTab(eit_tab=self._eit_tab)
        self._theory_tab  = TheoryTab()
        self._afc_tab     = PlaceholderTab(
            "AFC",
            "Atomic Frequency Comb memory uses a spectral grating of absorption peaks "
            "to store photon wavepackets via photon echoes.  Multi-mode capacity and "
            "on-demand retrieval make it ideal for quantum repeater nodes."
        )
        self._gem_tab     = PlaceholderTab(
            "GEM",
            "Gradient Echo Memory uses a reversible inhomogeneous broadening "
            "(magnetic or Stark gradient) to store and retrieve light pulses with "
            "high efficiency, high bandwidth, and large mode capacity."
        )

        self._tabs.addTab(self._eit_tab,    " EIT Simulation ")
        self._tabs.addTab(self._sweep_tab,  " Parameter Sweep ")
        self._tabs.addTab(self._theory_tab, " Theory & Background ")
        self._tabs.addTab(self._afc_tab,    " AFC (soon) ")
        self._tabs.addTab(self._gem_tab,    " GEM (soon) ")

        self.setCentralWidget(self._tabs)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_statusbar(self):
        sb = QStatusBar()
        sb.showMessage(
            f"{APP_TITLE} v{APP_VERSION}  |  EIT Maxwell-Bloch simulation  |  "
            "Run a simulation in the EIT tab to begin."
        )
        self.setStatusBar(sb)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _show_about(self):
        QMessageBox.information(
            self, "About",
            f"<b>{APP_TITLE}</b> v{APP_VERSION}<br><br>"
            "Modular quantum memory simulator supporting:<br>"
            "• <b>EIT</b> — Maxwell-Bloch equations (RK4 + numba)<br>"
            "• <b>AFC</b> — coming soon<br>"
            "• <b>GEM</b> — coming soon<br><br>"
            "Physics references:<br>"
            "Gorshkov et al., PRL 98, 123601 (2007)<br>"
            "Fleischhauer &amp; Lukin, PRL 84, 5094 (2000)"
        )
