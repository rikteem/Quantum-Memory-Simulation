"""
Reusable parameter-input widgets for the quantum memory GUI.

ParamSpinBox     — labelled float spinbox + unit label
ParamIntSpinBox  — labelled int spinbox
ParamChoice      — labelled combo box
ParamGroup       — collapsible group box that holds a set of ParamSpinBox
ParamPanel       — scrollable panel that auto-builds from a protocol's param_schema()
"""

from __future__ import annotations
from typing import Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QComboBox,
    QGroupBox, QScrollArea, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


# ---------------------------------------------------------------------------
# Individual parameter widgets
# ---------------------------------------------------------------------------

class ParamSpinBox(QWidget):
    """Labelled QDoubleSpinBox for a float parameter."""
    valueChanged = pyqtSignal(float)

    def __init__(self, label: str, value: float, min_val: float, max_val: float,
                 step: float = 0.1, decimals: int = 4, unit: str = "",
                 tooltip: str = "", parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 1, 2, 1)

        lbl = QLabel(label)
        lbl.setMinimumWidth(160)
        lbl.setToolTip(tooltip)
        row.addWidget(lbl)

        self._spin = QDoubleSpinBox()
        self._spin.setRange(min_val, max_val)
        self._spin.setSingleStep(step)
        self._spin.setDecimals(decimals)
        self._spin.setValue(value)
        self._spin.setToolTip(tooltip)
        self._spin.setMinimumWidth(90)
        row.addWidget(self._spin)

        if unit:
            row.addWidget(QLabel(unit))

        row.addStretch()
        self._spin.valueChanged.connect(self.valueChanged)

    def value(self) -> float:
        return self._spin.value()

    def setValue(self, v: float):
        self._spin.setValue(v)


class ParamIntSpinBox(QWidget):
    """Labelled QSpinBox for an integer parameter."""
    valueChanged = pyqtSignal(int)

    def __init__(self, label: str, value: int, min_val: int, max_val: int,
                 step: int = 1, unit: str = "", tooltip: str = "", parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 1, 2, 1)

        lbl = QLabel(label)
        lbl.setMinimumWidth(160)
        lbl.setToolTip(tooltip)
        row.addWidget(lbl)

        self._spin = QSpinBox()
        self._spin.setRange(min_val, max_val)
        self._spin.setSingleStep(step)
        self._spin.setValue(value)
        self._spin.setToolTip(tooltip)
        self._spin.setMinimumWidth(90)
        row.addWidget(self._spin)

        if unit:
            row.addWidget(QLabel(unit))
        row.addStretch()
        self._spin.valueChanged.connect(self.valueChanged)

    def value(self) -> int:
        return self._spin.value()

    def setValue(self, v: int):
        self._spin.setValue(v)


class ParamChoice(QWidget):
    """Labelled QComboBox for a discrete-choice parameter."""
    valueChanged = pyqtSignal(str)

    def __init__(self, label: str, choices: list[str], current: str = "",
                 tooltip: str = "", parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 1, 2, 1)

        lbl = QLabel(label)
        lbl.setMinimumWidth(160)
        lbl.setToolTip(tooltip)
        row.addWidget(lbl)

        self._combo = QComboBox()
        self._combo.addItems(choices)
        if current in choices:
            self._combo.setCurrentText(current)
        self._combo.setToolTip(tooltip)
        row.addWidget(self._combo)
        row.addStretch()
        self._combo.currentTextChanged.connect(self.valueChanged)

    def value(self) -> str:
        return self._combo.currentText()

    def setValue(self, v: str):
        self._combo.setCurrentText(v)


# ---------------------------------------------------------------------------
# Auto-building panel from schema
# ---------------------------------------------------------------------------

class ParamPanel(QScrollArea):
    """
    Scrollable parameter panel that builds itself from a protocol's
    param_schema() list and syncs values with a dict.
    """

    def __init__(self, schema: list[dict], defaults: dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setSpacing(4)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self.setWidget(container)

        self._widgets: dict[str, QWidget] = {}
        self._schema   = schema
        self._defaults = defaults

        self._build(schema, defaults)
        self._layout.addStretch()

    # ------------------------------------------------------------------

    def _build(self, schema: list[dict], defaults: dict):
        # Group widgets by their 'group' key
        groups: dict[str, list[dict]] = {}
        for s in schema:
            g = s.get("group", "General")
            groups.setdefault(g, []).append(s)

        for group_name, items in groups.items():
            box = QGroupBox(group_name)
            box.setFont(QFont("Segoe UI", 9, QFont.Bold))
            box_layout = QVBoxLayout(box)
            box_layout.setSpacing(2)

            for s in items:
                name     = s["name"]
                label    = s.get("label", name)
                typ      = s.get("type", "float")
                tooltip  = s.get("tooltip", "")
                default  = defaults.get(name)

                if typ == "float":
                    w = ParamSpinBox(
                        label, float(default if default is not None else 0),
                        s.get("min", 0), s.get("max", 1e6),
                        s.get("step", 0.1), s.get("decimals", 4),
                        s.get("unit", ""), tooltip,
                    )
                elif typ == "int":
                    w = ParamIntSpinBox(
                        label, int(default if default is not None else 0),
                        s.get("min", 0), s.get("max", 100000),
                        s.get("step", 1), s.get("unit", ""), tooltip,
                    )
                elif typ == "choice":
                    choices = [str(c) for c in s.get("choices", [])]
                    w = ParamChoice(label, choices, str(default or ""), tooltip)
                else:
                    continue

                self._widgets[name] = w
                box_layout.addWidget(w)

            self._layout.addWidget(box)

    # ------------------------------------------------------------------

    def get_params(self) -> dict[str, Any]:
        """Read all current widget values into a dict."""
        out = dict(self._defaults)  # start with defaults
        for name, w in self._widgets.items():
            val = w.value()
            # Cast back to expected Python type
            schema_entry = next((s for s in self._schema if s["name"] == name), {})
            if schema_entry.get("type") == "int":
                val = int(val)
            elif schema_entry.get("type") == "float":
                val = float(val)
            elif schema_entry.get("type") == "choice":
                # handle bool-like choice
                if val in ("True", "False"):
                    val = val == "True"
            out[name] = val
        return out

    def set_params(self, params: dict[str, Any]):
        """Push a params dict into the widgets."""
        for name, w in self._widgets.items():
            if name in params:
                w.setValue(params[name])

    def reset_defaults(self):
        """Reset all widgets to their default values."""
        self.set_params(self._defaults)
