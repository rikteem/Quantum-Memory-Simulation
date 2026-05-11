"""
EIT Simulation tab — the primary interactive panel.

Layout
──────
  Left  : ParamPanel (scrollable parameter controls) + Run/Stop + progress
  Right : QTabWidget with sub-tabs for:
            • Spatial   – E/P/S vs z at a selected time snapshot
            • Temporal  – E/P/S vs t at entrance / mid / exit
            • 3-D       – surface plot of E(z, t)
            • Control   – Rabi profile vs time
          Below plots: metrics text pane
"""

from __future__ import annotations
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QProgressBar, QLabel, QTextEdit,
    QTabWidget, QSlider, QSizePolicy,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFont

from protocols.eit.simulator import EITSimulator
from protocols.base_protocol import SimulationResult
from gui.widgets.param_widgets import ParamPanel
from gui.widgets.plot_canvas import PlotWidget


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class SimWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)   # SimulationResult or Exception
    error    = pyqtSignal(str)

    def __init__(self, params: dict):
        super().__init__()
        self._params = params
        self._sim    = EITSimulator()
        self._abort  = False

    def run(self):
        try:
            result = self._sim.run(self._params, self.progress.emit)
            if not self._abort:
                self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))

    def abort(self):
        self._abort = True


# ---------------------------------------------------------------------------
# EIT simulation tab
# ---------------------------------------------------------------------------

class EITTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: SimulationResult | None = None
        self._sim    = EITSimulator()
        self._worker_thread: QThread | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        main_split = QSplitter(Qt.Horizontal, self)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(main_split)

        # ---- Left panel ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)
        left.setMinimumWidth(280)
        left.setMaximumWidth(340)

        title = QLabel("EIT Parameters")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title)

        self._param_panel = ParamPanel(
            self._sim.param_schema(), self._sim.default_params()
        )
        left_layout.addWidget(self._param_panel, stretch=1)

        # Run controls
        btn_row = QHBoxLayout()
        self._btn_run  = QPushButton("▶  Run Simulation")
        self._btn_run.setStyleSheet("background:#a6e3a1; color:#1e1e2e; font-weight:bold; padding:6px;")
        self._btn_stop = QPushButton("■  Stop")
        self._btn_stop.setStyleSheet("background:#f38ba8; color:#1e1e2e; font-weight:bold; padding:6px;")
        self._btn_stop.setEnabled(False)
        btn_row.addWidget(self._btn_run)
        btn_row.addWidget(self._btn_stop)
        left_layout.addLayout(btn_row)

        self._btn_reset = QPushButton("Reset Defaults")
        self._btn_reset.setStyleSheet("background:#585b70; color:#cdd6f4; padding:4px;")
        left_layout.addWidget(self._btn_reset)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        left_layout.addWidget(self._progress)

        self._status_label = QLabel("Ready.")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet("color:#a6e3a1;")
        left_layout.addWidget(self._status_label)

        main_split.addWidget(left)

        # ---- Right panel ----
        right_split = QSplitter(Qt.Vertical)

        # Plot area (tabbed)
        self._plot_tabs = QTabWidget()
        self._plot_tabs.setTabPosition(QTabWidget.North)

        self._tab_spatial  = self._make_spatial_tab()
        self._tab_temporal = self._make_temporal_tab()
        self._tab_3d       = self._make_3d_tab()
        self._tab_control  = self._make_control_tab()

        self._plot_tabs.addTab(self._tab_spatial,  "Spatial")
        self._plot_tabs.addTab(self._tab_temporal, "Temporal")
        self._plot_tabs.addTab(self._tab_3d,       "3-D Surface")
        self._plot_tabs.addTab(self._tab_control,  "Control Field")

        right_split.addWidget(self._plot_tabs)

        # Metrics pane
        self._metrics_box = QTextEdit()
        self._metrics_box.setReadOnly(True)
        self._metrics_box.setMaximumHeight(150)
        self._metrics_box.setFont(QFont("Consolas", 9))
        self._metrics_box.setStyleSheet("background:#181825; color:#cdd6f4; border:none;")
        self._metrics_box.setPlaceholderText("Run a simulation to see metrics here.")
        right_split.addWidget(self._metrics_box)
        right_split.setSizes([600, 150])

        main_split.addWidget(right_split)
        main_split.setSizes([300, 900])

        # Signals
        self._btn_run.clicked.connect(self._on_run)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_reset.clicked.connect(self._param_panel.reset_defaults)
        self._plot_tabs.currentChanged.connect(self._refresh_current_tab)

    # ------------------------------------------------------------------
    # Sub-tab factories
    # ------------------------------------------------------------------

    def _make_spatial_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        self._spatial_plot = PlotWidget(n_rows=1, n_cols=1)
        layout.addWidget(self._spatial_plot)

        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Time slice:"))
        self._time_slider = QSlider(Qt.Horizontal)
        self._time_slider.setRange(0, 100)
        self._time_slider.setValue(0)
        self._time_label = QLabel("t = —")
        slider_row.addWidget(self._time_slider)
        slider_row.addWidget(self._time_label)
        layout.addLayout(slider_row)

        self._time_slider.valueChanged.connect(self._on_slider_changed)
        return w

    def _make_temporal_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        self._temporal_plot = PlotWidget(n_rows=3, n_cols=1)
        layout.addWidget(self._temporal_plot)
        return w

    def _make_3d_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        self._surf_plot = PlotWidget(n_rows=1, n_cols=1)
        layout.addWidget(self._surf_plot)
        return w

    def _make_control_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        self._ctrl_plot = PlotWidget(n_rows=1, n_cols=1)
        layout.addWidget(self._ctrl_plot)
        return w

    # ------------------------------------------------------------------
    # Simulation lifecycle
    # ------------------------------------------------------------------

    def _on_run(self):
        params = self._param_panel.get_params()
        self._progress.setValue(0)
        self._status_label.setText("Running… (JIT compiles on first run)")
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)

        self._worker = SimWorker(params)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._on_thread_done)

        self._worker_thread.start()

    def _on_stop(self):
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker.abort()
            self._worker_thread.quit()
            self._worker_thread.wait(2000)
        self._status_label.setText("Stopped.")
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_finished(self, result):
        self._result = result
        self._status_label.setText(
            f"Done in {result.metrics.get('run_time_s', '?')} s  |  "
            f"η = {result.metrics.get('efficiency', '?'):.3f}"
        )
        self._progress.setValue(100)
        self._time_slider.setRange(0, max(0, result.n_time - 1))
        self._time_slider.setValue(0)
        self._plot_all()
        self._show_metrics(result.metrics)

    def _on_error(self, msg: str):
        self._status_label.setText(f"Error: {msg}")
        self._metrics_box.setPlainText(f"Simulation error:\n{msg}")

    def _on_thread_done(self):
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def _plot_all(self):
        if self._result is None:
            return
        self._plot_spatial(0)
        self._plot_temporal()
        self._plot_3d()
        self._plot_control()

    def _refresh_current_tab(self, idx: int):
        if self._result is None:
            return
        tab_map = {0: self._plot_spatial, 1: self._plot_temporal,
                   2: self._plot_3d,      3: self._plot_control}
        fn = tab_map.get(idx)
        if fn:
            if idx == 0:
                fn(self._time_slider.value())
            else:
                fn()

    def _on_slider_changed(self, val: int):
        if self._result is None:
            return
        self._plot_spatial(val)
        t = self._result.t[val] if val < len(self._result.t) else 0
        self._time_label.setText(f"t = {t:.2f}")

    def _plot_spatial(self, t_idx: int = 0):
        r = self._result
        t_idx = min(t_idx, r.n_time - 1)
        pw = self._spatial_plot
        pw.clear_all()
        ax = pw._ax()
        ax.set_facecolor("#1e1e2e")
        ax.grid(True, alpha=0.3)

        ax.plot(r.z, r.E[t_idx], label="|E|", color="#89b4fa")
        ax.plot(r.z, r.P[t_idx], label="|P|", color="#a6e3a1", alpha=0.8)
        ax.plot(r.z, r.S[t_idx], label="|S|", color="#f38ba8", alpha=0.8)

        m = r.metrics
        ax.axvline(m["enter"], color="#fab387", ls="--", lw=1, label="Medium")
        ax.axvline(m["exit"],  color="#fab387", ls="--", lw=1)

        ax.set_xlabel("z (working units)", color="#cdd6f4")
        ax.set_ylabel("Amplitude", color="#cdd6f4")
        ax.set_title(f"Fields at t = {r.t[t_idx]:.2f}", color="#cba6f7")
        ax.legend(fontsize=8)
        pw.draw()

    def _plot_temporal(self):
        r = self._result
        pw = self._temporal_plot
        pw.clear_all()
        axes = pw.axes.flat

        m  = r.metrics
        i0 = max(0, m["enter_idx"] - 2)
        i1 = (m["enter_idx"] + m["exit_idx"]) // 2
        i2 = min(r.n_z - 1, m["exit_idx"] + 2)

        rabi_dense = r.rabi_profile
        t_dense    = r.t_dense

        for ax, field, name, color in zip(
            axes,
            [r.E, r.P, r.S],
            ["E (Signal)", "P (Polarisation)", "S (Spin wave)"],
            ["#89b4fa", "#a6e3a1", "#f38ba8"],
        ):
            ax.set_facecolor("#1e1e2e")
            ax.grid(True, alpha=0.3)
            ax.plot(r.t, field[:, i0], color=color,       lw=1.2, label="Entrance")
            ax.plot(r.t, field[:, i1], color=color,       lw=1.2, ls="--", label="Midpoint", alpha=0.8)
            ax.plot(r.t, field[:, i2], color=color,       lw=1.2, ls=":",  label="Exit",     alpha=0.8)
            ax2 = ax.twinx()
            ax2.plot(t_dense, rabi_dense, color="#f9e2af", lw=0.7, alpha=0.5)
            ax2.set_ylabel("Ω (GHz)", color="#f9e2af", fontsize=7)
            ax2.tick_params(axis="y", labelcolor="#f9e2af", labelsize=7)
            ax.set_ylabel(name, color="#cdd6f4", fontsize=8)
            ax.legend(fontsize=7, loc="upper right")

        axes[-1].set_xlabel("time (working units)", color="#cdd6f4")
        pw.fig.suptitle("Temporal evolution", color="#cba6f7")
        pw.draw()

    def _plot_3d(self):
        r = self._result
        pw = self._surf_plot
        pw.fig.clear()
        ax = pw.fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#1e1e2e")
        pw.fig.patch.set_facecolor("#1e1e2e")

        step = max(1, r.n_time // 80)   # downsample for speed
        t_sub = r.t[::step]
        E_sub = r.E[::step]

        T, Z = np.meshgrid(t_sub, r.z, indexing="ij")
        ax.plot_surface(T, Z, E_sub, cmap="plasma", alpha=0.85, linewidth=0)
        ax.set_xlabel("time", color="#cdd6f4", fontsize=8)
        ax.set_ylabel("z",    color="#cdd6f4", fontsize=8)
        ax.set_zlabel("E",    color="#cdd6f4", fontsize=8)
        ax.set_title("E(z, t) surface", color="#cba6f7")
        ax.tick_params(colors="#cdd6f4", labelsize=7)
        pw.canvas.draw()

    def _plot_control(self):
        r = self._result
        pw = self._ctrl_plot
        pw.clear_all()
        ax = pw._ax()
        ax.set_facecolor("#1e1e2e")
        ax.grid(True, alpha=0.3)
        ax.plot(r.t_dense, r.rabi_profile, color="#f9e2af", lw=1.5)
        ax.set_xlabel("time (working units)", color="#cdd6f4")
        ax.set_ylabel("Rabi frequency Ω (GHz)", color="#cdd6f4")
        ax.set_title("Control field temporal profile", color="#cba6f7")
        ax.fill_between(r.t_dense, r.rabi_profile, alpha=0.15, color="#f9e2af")
        pw.draw()

    # ------------------------------------------------------------------
    # Metrics display
    # ------------------------------------------------------------------

    def _show_metrics(self, m: dict):
        lines = [
            f"  Optical depth (OD)     : {m.get('optical_depth', '?')}",
            f"  Group velocity v_g     : {m.get('group_velocity', '?'):.4g}",
            f"  Slow-down factor c/v_g : {m.get('slow_down_factor', '?'):.1f}",
            f"  Storage efficiency η   : {m.get('efficiency', '?'):.4f}",
            f"  Time delay             : {m.get('time_delay', '?'):.3g}",
            f"  Grid points (z)        : {m.get('n_z', '?')}",
            f"  Time steps             : {m.get('n_steps', '?')}",
            f"  Wall-clock time        : {m.get('run_time_s', '?')} s",
        ]
        self._metrics_box.setPlainText("\n".join(lines))
