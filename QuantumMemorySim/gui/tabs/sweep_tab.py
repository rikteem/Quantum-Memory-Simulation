"""
Parameter Sweep tab — analytical/fast sweeps of EIT metrics vs one parameter.

Uses the analytical formulas from protocols/eit/analytics.py to compute metrics
instantly (no full MB simulation needed per point).
An option to run full MB sweeps (slow) is available for verification.
"""

from __future__ import annotations
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QSpinBox, QPushButton, QGroupBox,
    QCheckBox, QSplitter, QTextEdit,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from protocols.eit.analytics import (
    sweep_N, sweep_Omega, sweep_L, sweep_storage_time, optical_depth
)
from protocols.eit.simulator import EITSimulator
from gui.widgets.plot_canvas import PlotWidget


SWEEP_PARAMS = {
    "Atom number N":    {"key": "N",            "min": 10,   "max": 10000, "steps": 50, "log": True},
    "Control Rabi Ω":  {"key": "Omega",         "min": 1.0,  "max": 200.0, "steps": 50, "log": False},
    "Medium length L":  {"key": "L",            "min": 0.5,  "max": 20.0,  "steps": 40, "log": False},
    "Storage time":     {"key": "storage_time", "min": 1.0,  "max": 5000,  "steps": 50, "log": True},
}

OUTPUT_METRICS = [
    "efficiency", "OD", "vg", "time_delay", "eit_bandwidth",
]


class SweepTab(QWidget):
    def __init__(self, eit_tab=None, parent=None):
        super().__init__(parent)
        self._eit_tab = eit_tab   # reference to EIT tab to read current params
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        # ---- Left controls ----
        left = QWidget()
        left.setMaximumWidth(300)
        ll = QVBoxLayout(left)
        ll.setSpacing(8)

        title = QLabel("Parameter Sweep")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        ll.addWidget(title)

        # Sweep param selection
        grp_x = QGroupBox("X-axis: sweep parameter")
        gx = QVBoxLayout(grp_x)
        self._sweep_combo = QComboBox()
        self._sweep_combo.addItems(list(SWEEP_PARAMS.keys()))
        gx.addWidget(self._sweep_combo)

        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("Min:"))
        self._x_min = QDoubleSpinBox(); self._x_min.setRange(0, 1e7); self._x_min.setValue(10)
        range_row.addWidget(self._x_min)
        range_row.addWidget(QLabel("Max:"))
        self._x_max = QDoubleSpinBox(); self._x_max.setRange(0, 1e7); self._x_max.setValue(1000)
        range_row.addWidget(self._x_max)
        gx.addLayout(range_row)

        steps_row = QHBoxLayout()
        steps_row.addWidget(QLabel("Points:"))
        self._n_pts = QSpinBox(); self._n_pts.setRange(5, 500); self._n_pts.setValue(60)
        steps_row.addWidget(self._n_pts)
        self._log_scale = QCheckBox("Log scale X")
        steps_row.addWidget(self._log_scale)
        gx.addLayout(steps_row)
        ll.addWidget(grp_x)

        # Y-axis metric
        grp_y = QGroupBox("Y-axis: output metric")
        gy = QVBoxLayout(grp_y)
        self._metric_combo = QComboBox()
        self._metric_combo.addItems(OUTPUT_METRICS)
        gy.addWidget(self._metric_combo)
        ll.addWidget(grp_y)

        # Second-parameter overlay
        grp_p2 = QGroupBox("Overlay: 2nd parameter variation")
        gp2 = QVBoxLayout(grp_p2)
        self._overlay_combo = QComboBox()
        self._overlay_combo.addItem("None")
        self._overlay_combo.addItems([k for k in SWEEP_PARAMS if k != self._sweep_combo.currentText()])
        gp2.addWidget(self._overlay_combo)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Values (comma-sep):"))
        from PyQt5.QtWidgets import QLineEdit
        self._overlay_vals = QLineEdit("10,100,1000")
        row2.addWidget(self._overlay_vals)
        gp2.addLayout(row2)
        ll.addWidget(grp_p2)

        # Run button
        self._btn_sweep = QPushButton("▶  Run Sweep (Analytical)")
        self._btn_sweep.setStyleSheet("background:#89b4fa; color:#1e1e2e; font-weight:bold; padding:6px;")
        ll.addWidget(self._btn_sweep)

        self._info_box = QTextEdit()
        self._info_box.setReadOnly(True)
        self._info_box.setMaximumHeight(120)
        self._info_box.setFont(QFont("Consolas", 8))
        self._info_box.setStyleSheet("background:#181825; color:#cdd6f4;")
        ll.addWidget(self._info_box)
        ll.addStretch()

        root.addWidget(left)

        # ---- Right plot ----
        self._plot = PlotWidget(n_rows=1, n_cols=1, width=8, height=5)
        root.addWidget(self._plot, stretch=1)

        # Signals
        self._sweep_combo.currentTextChanged.connect(self._on_sweep_changed)
        self._btn_sweep.clicked.connect(self._run_sweep)
        self._on_sweep_changed(self._sweep_combo.currentText())

    def _on_sweep_changed(self, name: str):
        info = SWEEP_PARAMS.get(name, {})
        self._x_min.setValue(info.get("min", 0))
        self._x_max.setValue(info.get("max", 100))
        self._log_scale.setChecked(info.get("log", False))
        # Update overlay options
        self._overlay_combo.clear()
        self._overlay_combo.addItem("None")
        self._overlay_combo.addItems([k for k in SWEEP_PARAMS if k != name])

    def _get_base_params(self) -> dict:
        if self._eit_tab is not None:
            try:
                return self._eit_tab._param_panel.get_params()
            except Exception:
                pass
        return EITSimulator().default_params()

    def _run_sweep(self):
        p = self._get_base_params()
        sweep_name = self._sweep_combo.currentText()
        metric     = self._metric_combo.currentText()
        n_pts      = self._n_pts.value()
        x_min      = self._x_min.value()
        x_max      = self._x_max.value()
        use_log    = self._log_scale.isChecked()

        if use_log and x_min > 0:
            x_arr = np.logspace(np.log10(x_min), np.log10(x_max), n_pts)
        else:
            x_arr = np.linspace(x_min, x_max, n_pts)

        # Parse overlay values
        overlay_name = self._overlay_combo.currentText()
        if overlay_name != "None":
            try:
                overlay_vals = [float(v.strip()) for v in self._overlay_vals.text().split(",")]
            except ValueError:
                overlay_vals = []
        else:
            overlay_vals = []

        self._plot.clear_all()
        ax = self._plot._ax()
        ax.set_facecolor("#1e1e2e")
        ax.grid(True, alpha=0.3)

        colors = ["#89b4fa", "#a6e3a1", "#f38ba8", "#fab387", "#cba6f7"]

        def run_one(params_override: dict, label: str, color: str):
            q = {**p, **params_override}
            gamma_eg = 0.5 * (q["decay_e"] + q["dephase_e"])
            gamma_sg = 0.5 * q["dephase_s"]
            od0 = optical_depth(q["g"], q["N"], q["L"], q["c"], gamma_eg)

            if sweep_name == "Atom number N":
                data = sweep_N(x_arr, q["g"], q["L"], q["c"], gamma_eg, gamma_sg, q["Omega"])
            elif sweep_name == "Control Rabi Ω":
                data = sweep_Omega(x_arr, q["N"], q["g"], q["L"], q["c"], gamma_eg, gamma_sg)
            elif sweep_name == "Medium length L":
                data = sweep_L(x_arr, q["N"], q["g"], q["c"], gamma_eg, gamma_sg, q["Omega"])
            elif sweep_name == "Storage time":
                data = sweep_storage_time(x_arr, od0, gamma_sg, q["Omega"], gamma_eg)
            else:
                return

            y = data.get(metric, data.get(list(data.keys())[-1]))
            ax.plot(x_arr, y, color=color, lw=1.8, label=label)

        # Primary sweep
        run_one({}, "baseline", colors[0])

        # Overlay sweeps
        if overlay_name != "None" and overlay_vals:
            overlay_key = SWEEP_PARAMS[overlay_name]["key"]
            for i, val in enumerate(overlay_vals[:4]):
                run_one({overlay_key: val}, f"{overlay_name}={val}", colors[i + 1])

        xlabel_map = {
            "Atom number N":    "N (atoms)",
            "Control Rabi Ω":  "Ω (GHz)",
            "Medium length L":  "L (working units)",
            "Storage time":     "Storage time",
        }
        ylabel_map = {
            "efficiency":    "Storage efficiency η",
            "OD":            "Optical depth OD",
            "vg":            "Group velocity v_g",
            "time_delay":    "Time delay",
            "eit_bandwidth": "EIT bandwidth (GHz)",
        }
        ax.set_xlabel(xlabel_map.get(sweep_name, sweep_name), color="#cdd6f4")
        ax.set_ylabel(ylabel_map.get(metric, metric), color="#cdd6f4")
        ax.set_title(f"{metric} vs {sweep_name}", color="#cba6f7")
        if use_log:
            ax.set_xscale("log")
        if overlay_vals:
            ax.legend(fontsize=8)

        self._plot.draw()
        self._info_box.setPlainText(
            f"Sweep: {sweep_name}  [{x_min:.3g} → {x_max:.3g}]  ({n_pts} pts)\n"
            f"Metric: {metric}\n"
            f"Base OD = {optical_depth(p['g'], p['N'], p['L'], p['c'], 0.5*(p['decay_e']+p['dephase_e'])):.2f}\n"
            f"Method: analytical (instant)"
        )
