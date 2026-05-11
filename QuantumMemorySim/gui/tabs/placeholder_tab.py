"""Placeholder tab for protocols not yet implemented (AFC, GEM)."""

from __future__ import annotations
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class PlaceholderTab(QWidget):
    def __init__(self, protocol_name: str, description: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("🔬")
        icon.setFont(QFont("Segoe UI Emoji", 48))
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel(f"{protocol_name}\nQuantum Memory")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color:#cba6f7;")
        layout.addWidget(title)

        status = QLabel("Coming Soon")
        status.setFont(QFont("Segoe UI", 14))
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet(
            "color:#f9e2af; background:#313244; padding:8px 20px; border-radius:6px;"
        )
        layout.addWidget(status)

        if description:
            desc = QLabel(description)
            desc.setFont(QFont("Segoe UI", 10))
            desc.setAlignment(Qt.AlignCenter)
            desc.setWordWrap(True)
            desc.setStyleSheet("color:#a6adc8; max-width:500px; margin-top:16px;")
            layout.addWidget(desc)
