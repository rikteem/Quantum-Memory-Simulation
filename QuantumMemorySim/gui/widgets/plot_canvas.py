"""
Reusable matplotlib canvas widget for PyQt5.

Provides:
  MplCanvas  — embeds a Figure in a QWidget
  PlotToolbar — navigation toolbar (zoom/pan/save)
"""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy


class MplCanvas(FigureCanvas):
    """A matplotlib figure canvas that fits inside a QWidget layout."""

    def __init__(self, parent=None, width: float = 8, height: float = 6,
                 dpi: int = 100, n_rows: int = 1, n_cols: int = 1):
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.fig.patch.set_facecolor("#1e1e2e")   # dark background

        if n_rows * n_cols > 1:
            self.axes = self.fig.subplots(n_rows, n_cols)
        else:
            self.axes = self.fig.add_subplot(111)

        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()

    def _ax(self, idx: int | tuple | None = None):
        """Return a single axes object by flat index or (row, col)."""
        if idx is None:
            return self.axes
        if isinstance(self.axes, np.ndarray):
            if isinstance(idx, tuple):
                return self.axes[idx]
            return self.axes.flat[idx]
        return self.axes

    def clear_all(self):
        """Clear all axes."""
        if isinstance(self.axes, np.ndarray):
            for ax in self.axes.flat:
                ax.clear()
        else:
            self.axes.clear()


class PlotWidget(QWidget):
    """
    A self-contained widget combining MplCanvas + NavigationToolbar.
    Drop this into any layout for a complete plot pane.
    """

    def __init__(self, parent=None, width: float = 8, height: float = 5,
                 dpi: int = 100, n_rows: int = 1, n_cols: int = 1):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.canvas = MplCanvas(self, width=width, height=height,
                                dpi=dpi, n_rows=n_rows, n_cols=n_cols)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

    # Convenience passthrough
    @property
    def fig(self):
        return self.canvas.fig

    @property
    def axes(self):
        return self.canvas.axes

    def _ax(self, idx=None):
        return self.canvas._ax(idx)

    def draw(self):
        self.canvas.draw()

    def clear_all(self):
        self.canvas.clear_all()


# ---------------------------------------------------------------------------
# Dark-theme matplotlib style applied once at import time
# ---------------------------------------------------------------------------
import matplotlib as mpl

DARK_STYLE = {
    "axes.facecolor":    "#1e1e2e",
    "axes.edgecolor":    "#cdd6f4",
    "axes.labelcolor":   "#cdd6f4",
    "axes.titlecolor":   "#cba6f7",
    "axes.prop_cycle":   mpl.cycler(color=[
        "#89b4fa", "#a6e3a1", "#f38ba8",
        "#fab387", "#f9e2af", "#cba6f7",
        "#94e2d5", "#89dceb",
    ]),
    "figure.facecolor":  "#1e1e2e",
    "text.color":        "#cdd6f4",
    "xtick.color":       "#cdd6f4",
    "ytick.color":       "#cdd6f4",
    "grid.color":        "#313244",
    "grid.linestyle":    "--",
    "grid.alpha":        0.5,
    "legend.facecolor":  "#313244",
    "legend.edgecolor":  "#585b70",
    "legend.labelcolor": "#cdd6f4",
    "lines.linewidth":   1.5,
}

mpl.rcParams.update(DARK_STYLE)
