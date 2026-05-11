"""
Quantum Memory Simulator — Dash / React application.

Run:   python app_dash.py
Opens: http://localhost:8050
"""
from __future__ import annotations
import sys, os, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import dash
from dash import dcc, html, Input, Output, State, no_update, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from protocols.eit.simulator import EITSimulator
from protocols.eit.analytics import (
    sweep_N, sweep_Omega, sweep_L, sweep_storage_time, optical_depth
)
from gui.tabs.theory_tab import THEORY_HTML as _THEORY_HTML

# ─── Singletons & global state ──────────────────────────────────────────────
_SIM      = EITSimulator()
_DEFAULTS = _SIM.default_params()
_SCHEMA   = _SIM.param_schema()
_state: dict = {"running": False, "progress": 0, "result": None, "error": None}


# ─── Colour palettes ─────────────────────────────────────────────────────────
def _pal(theme: str) -> dict:
    """Hex colour dict for Plotly (CSS vars can't be used inside Plotly layout)."""
    if theme == "light":
        return dict(
            BG="#eff1f5",  BG2="#e6e9ef",
            E="#1e66f5",   P="#40a02b",   S="#d20f39",
            OHM="#df8e1d", MED="#fe640b",
            TXT="#4c4f69", TTL="#1e66f5", SUB="#6c6f85",
            TMPL="plotly_white",
        )
    return dict(
        BG="#1e1e2e",  BG2="#181825",
        E="#89b4fa",   P="#a6e3a1",   S="#f38ba8",
        OHM="#f9e2af", MED="#fab387",
        TXT="#cdd6f4", TTL="#89b4fa", SUB="#a6adc8",
        TMPL="plotly_dark",
    )


def _empty_fig(theme: str = "dark", msg: str = "Run a simulation to populate this plot.") -> go.Figure:
    c = _pal(theme)
    fig = go.Figure()
    fig.update_layout(
        template=c["TMPL"], paper_bgcolor=c["BG"], plot_bgcolor=c["BG2"],
        font=dict(color=c["TXT"]),
        title=dict(text=msg, font=dict(color=c["SUB"], size=12)),
        margin=dict(l=50, r=20, t=50, b=40),
    )
    return fig


# ─── Sidebar widgets ─────────────────────────────────────────────────────────
def _num_input(name: str, schema_entry: dict, default_val) -> dbc.Input:
    return dbc.Input(
        id={"type": "param-input", "index": name},
        type="number", value=default_val,
        min=schema_entry.get("min"),
        max=schema_entry.get("max"),
        step=schema_entry.get("step", 0.01),
        debounce=True, size="sm",
        className="qm-input w-100",
    )


def _choice_input(name: str, choices: list, default_val) -> dcc.Dropdown:
    return dcc.Dropdown(
        id={"type": "param-input", "index": name},
        options=[{"label": ch, "value": ch} for ch in choices],
        value=str(default_val),
        clearable=False,
        className="dark-dropdown",
        style={"fontSize": "0.8rem"},
    )


def _param_row(s: dict, defaults: dict) -> html.Div:
    """Stacked label-over-input layout — avoids horizontal overflow."""
    name    = s["name"]
    label   = s.get("label", name)
    unit    = s.get("unit", "")
    typ     = s.get("type", "float")
    tooltip = s.get("tooltip", "")
    default = defaults.get(name)

    lbl  = f"{label}  [{unit}]" if unit else label
    ctrl = (_num_input(name, s, default) if typ in ("float", "int")
            else _choice_input(name, s.get("choices", []), default))

    return html.Div([
        html.Label(lbl, title=tooltip,
                   style={"fontSize": "0.71rem", "color": "var(--qm-sub)",
                          "display": "block", "marginBottom": "2px",
                          "lineHeight": "1.15", "cursor": "help",
                          "fontWeight": "500"}),
        ctrl,
    ], style={"marginBottom": "7px"})


def _make_sidebar() -> dbc.Col:
    groups: dict[str, list] = {}
    for s in _SCHEMA:
        g = s.get("group", "General")
        groups.setdefault(g, []).append(s)

    all_group_ids = list(groups.keys())
    items = [
        dbc.AccordionItem([_param_row(s, _DEFAULTS) for s in entries],
                          title=grp, item_id=grp)
        for grp, entries in groups.items()
    ]

    # Default OD for placeholder text
    _geg0 = 0.5 * (_DEFAULTS["decay_e"] + _DEFAULTS["dephase_e"])
    _od0  = optical_depth(_DEFAULTS["g"], _DEFAULTS["N"], _DEFAULTS["L"],
                          _DEFAULTS["c"], _geg0)

    return dbc.Col(
        [
            html.H5("⚛  EIT Parameters", className="text-center mb-2",
                    style={"color": "var(--qm-ttl)", "fontWeight": "800",
                           "fontSize": "0.92rem", "letterSpacing": "0.5px"}),

            # ── Optical-depth quick-set ────────────────────────────────────
            html.Div([
                html.Div([
                    html.Span("Optical Depth",
                              style={"fontSize": "0.73rem", "fontWeight": "700",
                                     "color": "var(--qm-ttl)"}),
                    html.Span(" (auto-sets N)",
                              style={"fontSize": "0.67rem", "color": "var(--qm-sub)"}),
                ], style={"marginBottom": "4px"}),
                dbc.Row([
                    dbc.Col(
                        dbc.Input(id="od-input", type="number",
                                  placeholder=f"{_od0:.0f}",
                                  min=1, max=500000, step=10,
                                  debounce=True, size="sm",
                                  className="qm-input"),
                        width=6,
                    ),
                    dbc.Col(
                        html.Div(id="od-display",
                                 children=f"OD = {_od0:.1f}",
                                 style={"fontSize": "0.8rem",
                                        "color": "var(--qm-green)",
                                        "fontWeight": "700",
                                        "paddingTop": "5px"}),
                        width=6,
                    ),
                ], className="g-1"),
            ], className="qm-od-box mb-2"),

            # ── All parameter groups (all open by default) ─────────────────
            dbc.Accordion(
                items,
                always_open=True,
                active_item=all_group_ids,
                id="param-accordion",
                className="mb-3",
            ),

            dbc.Button("▶  Run Simulation", id="btn-run",
                       className="w-100 mb-2 qm-btn-run",
                       style={"fontWeight": "700", "letterSpacing": "0.5px"}),
            dbc.Button("■  Stop", id="btn-stop",
                       color="danger", className="w-100 mb-2", disabled=True),
            dbc.Button("↺  Reset Defaults", id="btn-reset",
                       color="secondary", size="sm", className="w-100 mb-3"),
            dbc.Progress(id="progress-bar", value=0, striped=True, animated=False,
                         className="mb-2 qm-progress"),
            html.Div(id="status-label", children="Ready.",
                     style={"fontSize": "0.73rem", "color": "var(--qm-sub)",
                            "textAlign": "center", "minHeight": "18px"}),
        ],
        width=3,
        className="qm-sidebar",
        style={"height": "100vh", "overflowY": "auto"},
    )


# ─── Animated spatial figure builder ────────────────────────────────────────
_SPEED_OPTIONS = [
    {"label": "Very Slow  (250 ms/frame)", "value": 250},
    {"label": "Slow       (150 ms/frame)", "value": 150},
    {"label": "Normal     (80 ms/frame)",  "value": 80},
    {"label": "Fast       (40 ms/frame)",  "value": 40},
    {"label": "Very Fast  (20 ms/frame)",  "value": 20},
]


def _build_spatial_anim(r, c: dict, speed_ms: int = 80) -> go.Figure:
    """Animated spatial figure using normalized Re(field) — matches notebook MP4 style."""
    m = r.metrics

    # Use real parts if available, fall back to abs values
    E_src = r.E_real if r.E_real is not None else r.E
    P_src = r.P_real if r.P_real is not None else r.P
    S_src = r.S_real if r.S_real is not None else r.S

    # Normalize each field to its global maximum (→ [-1, 1] range)
    E_max = np.abs(E_src).max(); E_n = E_src / E_max if E_max > 0 else E_src
    P_max = np.abs(P_src).max(); P_n = P_src / P_max if P_max > 0 else P_src
    S_max = np.abs(S_src).max(); S_n = S_src / S_max if S_max > 0 else S_src

    # Subsample: ≤35 frames, ≤300 spatial points
    n_frames  = min(35, r.n_time)
    frame_idx = np.linspace(0, r.n_time - 1, n_frames, dtype=int)
    z_step = max(1, r.n_z // 300)
    z_ds = r.z[::z_step]
    E_ds = E_n[:, ::z_step]
    P_ds = P_n[:, ::z_step]
    S_ds = S_n[:, ::z_step]

    # Colours matching the notebook (steelblue / tomato / darkorchid)
    col_E = "#4682b4"   # steelblue
    col_P = "#e05555"   # tomato
    col_S = "#8a4fbf"   # darkorchid

    # Use dark/light aware colours from the palette for medium shading
    med_col = c["MED"]

    i0 = frame_idx[0]
    t0 = r.t[i0]

    fig = go.Figure([
        go.Scatter(x=z_ds, y=E_ds[i0], name="E  (probe) — normalised",
                   line=dict(color=col_E, width=2.5)),
        go.Scatter(x=z_ds, y=P_ds[i0], name="P  (polariz.) — normalised",
                   line=dict(color=col_P, width=2.0)),
        go.Scatter(x=z_ds, y=S_ds[i0], name="S  (spin wave) — normalised",
                   line=dict(color=col_S, width=2.0)),
    ])

    # Build frames with instant-redraw slider (duration=0 in each step)
    fig.frames = [
        go.Frame(
            data=[
                go.Scatter(x=z_ds, y=E_ds[ti]),
                go.Scatter(x=z_ds, y=P_ds[ti]),
                go.Scatter(x=z_ds, y=S_ds[ti]),
            ],
            name=str(fi),
            layout=go.Layout(
                title=dict(
                    text=f"Re(field) [normalised]   t = {r.t[ti]:.1f} ns   "
                         f"Ω = {r.rabi_profile[min(int(r.t[ti]/max(r.t_dense[1]-r.t_dense[0],1e-9)), len(r.rabi_profile)-1)]:.1f} GHz",
                    font=dict(color=c["TTL"], size=14),
                ),
            ),
        )
        for fi, ti in enumerate(frame_idx)
    ]

    # Slider steps: duration=0 so dragging is instant
    slider_steps = [
        dict(method="animate",
             args=[[str(fi)],
                   dict(mode="immediate",
                        frame=dict(duration=0, redraw=True),
                        transition=dict(duration=0))],
             label=f"{r.t[ti]:.0f}")
        for fi, ti in enumerate(frame_idx)
    ]

    fig.update_layout(
        template=c["TMPL"],
        paper_bgcolor=c["BG"],
        plot_bgcolor=c["BG2"],
        font=dict(color=c["TXT"], size=13),
        title=dict(
            text=f"Re(field) [normalised]   t = {t0:.1f} ns",
            font=dict(color=c["TTL"], size=14),
        ),
        xaxis=dict(title=dict(text="z [mm]", font=dict(size=13)), color=c["TXT"]),
        yaxis=dict(title=dict(text="Amplitude (normalised)", font=dict(size=13)),
                   range=[-1.25, 1.25], color=c["TXT"],
                   zeroline=True, zerolinecolor=c["SUB"], zerolinewidth=1),
        # Legend goes BELOW the plot so it never collides with Play/Pause buttons
        legend=dict(orientation="h", x=0.5, xanchor="center",
                    y=-0.22, yanchor="top", font=dict(size=11)),
        margin=dict(l=60, r=20, t=130, b=120),
        # Medium shading and boundaries
        shapes=[
            dict(type="rect",
                 x0=m["enter"], x1=m["exit"], y0=-1.25, y1=1.25,
                 fillcolor="rgba(80,200,80,0.07)", line=dict(width=0)),
            dict(type="line", x0=m["enter"], x1=m["enter"], y0=-1.25, y1=1.25,
                 line=dict(color=med_col, dash="dash", width=1.5)),
            dict(type="line", x0=m["exit"],  x1=m["exit"],  y0=-1.25, y1=1.25,
                 line=dict(color=med_col, dash="dot", width=1.5)),
        ],
        annotations=[
            dict(x=m["enter"], y=1.18, text="← Medium →", showarrow=False,
                 font=dict(color=med_col, size=10), xanchor="left"),
        ],
        # Play/Pause buttons — placed well above the plot
        updatemenus=[dict(
            type="buttons", showactive=False,
            y=1.28, x=0.0, xanchor="left", yanchor="top",
            pad=dict(r=10, t=0),
            buttons=[
                dict(label="▶  Play", method="animate",
                     args=[None, dict(frame=dict(duration=speed_ms, redraw=True),
                                      fromcurrent=True, mode="immediate",
                                      transition=dict(duration=0))]),
                dict(label="⏸  Pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
        sliders=[dict(
            steps=slider_steps,
            active=0,
            x=0.0, len=1.0,
            y=0, yanchor="top",
            pad=dict(b=5, t=45),
            currentvalue=dict(
                prefix="t = ", suffix=" ns",
                visible=True, xanchor="center",
                font=dict(color=c["TXT"], size=12),
            ),
            bgcolor="rgba(128,128,128,0.10)",
            bordercolor=c["SUB"],
            tickcolor=c["SUB"],
            font=dict(color=c["TXT"], size=9),
            minorticklen=0,
        )],
    )
    return fig


# ─── Parameter Sweep content ─────────────────────────────────────────────────
_SWEEP_PARAMS  = ["Atom number N", "Control Rabi Ω", "Medium length L", "Storage time"]
_SWEEP_METRICS = ["efficiency", "OD", "vg", "time_delay", "eit_bandwidth"]

_SWEEP_CONTENT = html.Div([
    dbc.Row([
        dbc.Col([
            html.H6("Sweep parameter", className="qm-subtitle"),
            dcc.Dropdown(id="sweep-param", options=_SWEEP_PARAMS,
                         value=_SWEEP_PARAMS[0], clearable=False,
                         className="dark-dropdown mb-2"),
            dbc.Row([
                dbc.Col([html.Label("Min", className="qm-label"),
                         dbc.Input(id="sweep-min", type="number", value=10,
                                   size="sm", className="qm-input")], width=6),
                dbc.Col([html.Label("Max", className="qm-label"),
                         dbc.Input(id="sweep-max", type="number", value=1000,
                                   size="sm", className="qm-input")], width=6),
            ], className="mb-2"),
            dbc.Row([
                dbc.Col([html.Label("Points", className="qm-label"),
                         dbc.Input(id="sweep-pts", type="number", value=60,
                                   min=5, max=500, size="sm", className="qm-input")], width=6),
                dbc.Col(
                    dbc.Checklist(
                        options=[{"label": " Log X", "value": "log"}],
                        value=[], id="sweep-logx",
                        style={"color": "var(--qm-txt)", "marginTop": "20px",
                               "fontSize": "0.8rem"},
                    ),
                    width=6,
                ),
            ], className="mb-2"),
            html.H6("Output metric", className="qm-subtitle"),
            dcc.Dropdown(id="sweep-metric", options=_SWEEP_METRICS,
                         value="efficiency", clearable=False,
                         className="dark-dropdown mb-2"),
            html.H6("Overlay (2nd param)", className="qm-subtitle"),
            dcc.Dropdown(id="sweep-overlay-param",
                         options=["None"] + _SWEEP_PARAMS,
                         value="None", clearable=False,
                         className="dark-dropdown mb-1"),
            dbc.Input(id="sweep-overlay-vals", type="text",
                      placeholder="e.g.  10, 100, 1000",
                      value="10,100,1000", size="sm",
                      className="qm-input mb-3"),
            dbc.Button("▶  Run Sweep", id="btn-sweep",
                       color="info", className="w-100 mb-2"),
            html.Pre(id="sweep-info", children="", className="qm-pre",
                     style={"marginTop": "8px"}),
        ], width=3, className="qm-sidebar-col"),
        dbc.Col(
            dcc.Graph(id="plot-sweep",
                      figure=_empty_fig(msg="Run a sweep to see results."),
                      style={"height": "520px"}),
            width=9,
        ),
    ], style={"minHeight": "560px"}),
])


# ─── App & layout ────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="Quantum Memory Simulator",
    suppress_callback_exceptions=True,
)


def _placeholder_tab(name: str, desc: str, tab_id: str) -> dbc.Tab:
    return dbc.Tab(
        html.Div([
            html.H2(f"{name}  Quantum Memory",
                    style={"color": "var(--qm-ttl)", "marginBottom": "12px"}),
            dbc.Badge("Coming Soon", color="warning",
                      style={"fontSize": "1rem", "padding": "8px 20px"}),
            html.P(desc, style={"color": "var(--qm-sub)", "marginTop": "16px",
                                 "maxWidth": "500px"}),
        ], style={"display": "flex", "flexDirection": "column",
                  "alignItems": "center", "justifyContent": "center",
                  "height": "500px"}),
        label=f" {name} (soon) ", tab_id=tab_id,
    )


_EIT_TAB = dbc.Tab(
    dbc.Tabs(
        [
            # ── Spatial: animated play/pause + speed control ───────────────
            dbc.Tab(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Span("Playback speed:",
                                          style={"fontSize": "0.8rem",
                                                 "color": "var(--qm-sub)",
                                                 "lineHeight": "30px"}),
                                width="auto",
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id="anim-speed-select",
                                    options=_SPEED_OPTIONS,
                                    value=80,
                                    clearable=False,
                                    className="dark-dropdown",
                                    style={"width": "210px", "fontSize": "0.8rem"},
                                ),
                                width="auto",
                            ),
                        ],
                        className="mb-1 mt-1 ms-1 g-2 align-items-center",
                    ),
                    dcc.Graph(
                        id="plot-spatial",
                        figure=_empty_fig(msg="Run a simulation — spatial animation appears here."),
                        style={"height": "450px"},
                    ),
                    html.Hr(style={"borderColor": "var(--qm-border)", "margin": "4px 0"}),
                    html.Pre(
                        id="metrics-text",
                        children="Run a simulation to see metrics.",
                        className="qm-pre",
                        style={"maxHeight": "120px", "overflowY": "auto"},
                    ),
                ],
                label="Spatial", tab_id="st-spatial",
            ),
            dbc.Tab(
                dcc.Graph(id="plot-temporal", figure=_empty_fig(),
                          style={"height": "520px"}),
                label="Temporal", tab_id="st-temporal",
            ),
            dbc.Tab(
                dcc.Graph(id="plot-snapshots", figure=_empty_fig(), style={"height": "520px"}),
                label="Snapshots", tab_id="st-snapshots",
            ),
            dbc.Tab(
                dcc.Graph(id="plot-3d", figure=_empty_fig(),
                          style={"height": "520px"}),
                label="3-D Surface", tab_id="st-3d",
            ),
            dbc.Tab(
                dcc.Graph(id="plot-control", figure=_empty_fig(),
                          style={"height": "520px"}),
                label="Control Field", tab_id="st-control",
            ),
            dbc.Tab(_SWEEP_CONTENT, label="Parameter Sweep", tab_id="st-sweep"),
            dbc.Tab(
                html.Iframe(srcDoc=_THEORY_HTML,
                            style={"width": "100%", "height": "560px",
                                   "border": "none"}),
                label="Theory & Background", tab_id="st-theory",
            ),
        ],
        id="eit-subtabs",
        active_tab="st-spatial",
    ),
    label=" EIT Simulation ", tab_id="tab-eit",
)

_AFC_TAB = _placeholder_tab(
    "AFC",
    "Atomic Frequency Comb memory stores photon wavepackets via a spectral grating "
    "of absorption peaks.  On-demand retrieval via a control field reversal.",
    "tab-afc",
)
_GEM_TAB = _placeholder_tab(
    "GEM",
    "Gradient Echo Memory uses a reversible inhomogeneous Stark/Zeeman broadening "
    "gradient to store and retrieve light pulses with high efficiency and mode capacity.",
    "tab-gem",
)

app.layout = dbc.Container(
    [
        dcc.Store(id="params-store", data=dict(_DEFAULTS)),
        dcc.Store(id="result-flag",  data=None),
        dcc.Store(id="theme-store",  data="dark"),
        dcc.Interval(id="sim-interval", interval=400, n_intervals=0, disabled=True),

        # ── Header ───────────────────────────────────────────────────────────
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.Span("⚛ ", style={"fontSize": "1.3rem"}),
                            html.Span("Quantum Memory Simulator",
                                      style={"fontWeight": "800",
                                             "letterSpacing": "1.5px",
                                             "fontSize": "1.12rem"}),
                            html.Span("  ·  Maxwell-Bloch · EIT · AFC · GEM",
                                      style={"fontSize": "0.75rem",
                                             "opacity": "0.65",
                                             "marginLeft": "10px"}),
                        ],
                        style={"color": "var(--qm-ttl)", "padding": "10px 4px"},
                    ),
                    width=9,
                ),
                dbc.Col(
                    dbc.Button("☀ Light / 🌙 Dark", id="btn-theme",
                               size="sm", className="qm-theme-btn mt-2 mb-1"),
                    width=3, className="text-end pe-4",
                ),
            ],
            className="qm-header",
        ),

        # ── Body ─────────────────────────────────────────────────────────────
        dbc.Row(
            [
                _make_sidebar(),
                dbc.Col(
                    dbc.Tabs(
                        [_EIT_TAB, _AFC_TAB, _GEM_TAB],
                        id="main-tabs",
                        active_tab="tab-eit",
                    ),
                    width=9,
                    style={"padding": "6px 8px"},
                ),
            ],
            style={"height": "calc(100vh - 52px)", "margin": "0"},
        ),
    ],
    fluid=True,
    className="qm-root",
    style={"padding": "0", "minHeight": "100vh"},
)


# ─── Callbacks ───────────────────────────────────────────────────────────────

# 1. Collect param inputs → params-store
@app.callback(
    Output("params-store", "data"),
    Input({"type": "param-input", "index": ALL}, "value"),
    State({"type": "param-input", "index": ALL}, "id"),
    prevent_initial_call=True,
)
def _update_params(values, ids):
    params = dict(_DEFAULTS)
    for val, id_dict in zip(values, ids):
        name = id_dict["index"]
        if val is None:
            continue
        schema_entry = next((s for s in _SCHEMA if s["name"] == name), {})
        typ = schema_entry.get("type", "float")
        if typ == "int":
            params[name] = int(val)
        elif typ == "choice":
            params[name] = (val == "True") if val in ("True", "False") else val
        else:
            params[name] = float(val)
    return params


# 2. Optical Depth input → back-calculate N
@app.callback(
    Output({"type": "param-input", "index": "N"}, "value"),
    Input("od-input", "value"),
    State("params-store", "data"),
    prevent_initial_call=True,
)
def _od_to_N(od_target, params):
    if od_target is None or od_target <= 0:
        return no_update
    p       = params or _DEFAULTS
    gamma_eg = 0.5 * (p["decay_e"] + p["dephase_e"])
    g2 = p["g"] ** 2
    L  = p["L"]
    c  = p["c"]
    if g2 * L * c == 0 or gamma_eg == 0:
        return no_update
    N = od_target * c * gamma_eg / (g2 * L)
    return max(1, int(round(N)))


# 3. params-store → live OD display
@app.callback(
    Output("od-display", "children"),
    Input("params-store", "data"),
)
def _update_od_display(params):
    p       = params or _DEFAULTS
    gamma_eg = 0.5 * (p["decay_e"] + p["dephase_e"])
    od = optical_depth(float(p["g"]), float(p["N"]), float(p["L"]),
                       float(p["c"]), gamma_eg)
    return f"OD = {od:.1f}"


# 4. Run / Stop buttons
@app.callback(
    Output("sim-interval", "disabled"),
    Output("btn-run",      "disabled"),
    Output("btn-stop",     "disabled"),
    Output("progress-bar", "value"),
    Output("status-label", "children"),
    Input("btn-run",  "n_clicks"),
    Input("btn-stop", "n_clicks"),
    State("params-store", "data"),
    prevent_initial_call=True,
)
def _run_stop(run_clicks, stop_clicks, params):
    trigger = dash.ctx.triggered_id
    if trigger == "btn-run":
        _state.update({"running": True, "progress": 0, "result": None, "error": None})

        def _worker():
            try:
                def _cb(pct): _state.__setitem__("progress", pct)
                result = _SIM.run(params or _DEFAULTS, _cb)
                _state["result"] = result
            except Exception as e:
                _state["error"] = str(e)
            finally:
                _state["running"] = False

        threading.Thread(target=_worker, daemon=True).start()
        return False, True, False, 0, "Running… (JIT compiles on first run ~10 s)"
    _state["running"] = False
    return True, False, True, _state["progress"], "Stopped."


# 5. Poll progress every 400 ms
@app.callback(
    Output("progress-bar", "value",    allow_duplicate=True),
    Output("progress-bar", "animated", allow_duplicate=True),
    Output("status-label", "children", allow_duplicate=True),
    Output("btn-run",      "disabled", allow_duplicate=True),
    Output("btn-stop",     "disabled", allow_duplicate=True),
    Output("sim-interval", "disabled", allow_duplicate=True),
    Output("result-flag",  "data"),
    Input("sim-interval", "n_intervals"),
    prevent_initial_call=True,
)
def _poll(n):
    if _state["error"]:
        return 0, False, f"Error: {_state['error']}", False, True, True, no_update
    pct = _state["progress"]
    if _state["running"]:
        return pct, True, f"Running… {pct}%", True, False, False, no_update
    if _state["result"] is not None:
        m   = _state["result"].metrics
        eta = m.get("efficiency", "?")
        t_s = m.get("run_time_s", "?")
        return 100, False, f"Done in {t_s} s  |  η = {eta:.3f}", False, True, True, n
    return pct, False, "Ready.", False, True, True, no_update


# 6. Draw static plots: temporal, 3D, control, metrics, snapshots
@app.callback(
    Output("plot-temporal",  "figure"),
    Output("plot-3d",        "figure"),
    Output("plot-control",   "figure"),
    Output("plot-snapshots", "figure"),
    Output("metrics-text",   "children"),
    Input("result-flag", "data"),
    Input("theme-store", "data"),
    prevent_initial_call=True,
)
def _draw_static(flag, theme):
    r = _state.get("result")
    c = _pal(theme or "dark")

    if r is None:
        ef = _empty_fig(theme or "dark")
        return ef, ef, ef, ef, "Run a simulation to see metrics."

    m       = r.metrics
    i_enter = m["enter_idx"]
    i_exit  = m["exit_idx"]
    i0 = max(0, i_enter - 2)
    i1 = (i_enter + i_exit) // 2
    i2 = min(r.n_z - 1, i_exit + 2)

    # ── Temporal ──────────────────────────────────────────────────────────────
    fig_t = make_subplots(rows=3, cols=1, shared_xaxes=True,
                          subplot_titles=["|E|  signal",
                                          "|P|  polarisation",
                                          "|S|  spin-wave"],
                          vertical_spacing=0.07)
    for row, (field, col) in enumerate([(r.E, c["E"]),
                                         (r.P, c["P"]),
                                         (r.S, c["S"])], start=1):
        for idx, dstyle, lbl in [(i0, "solid", "Entrance"),
                                  (i1, "dash",  "Mid"),
                                  (i2, "dot",   "Exit")]:
            fig_t.add_trace(
                go.Scatter(x=r.t, y=field[:, idx], name=lbl if row == 1 else None,
                           line=dict(color=col, dash=dstyle, width=1.5),
                           showlegend=(row == 1)),
                row=row, col=1,
            )
        scale   = max(field.max() * 0.3, 1e-9)
        rabi_sc = r.rabi_profile / (r.rabi_profile.max() or 1) * scale
        fig_t.add_trace(
            go.Scatter(x=r.t_dense, y=rabi_sc,
                       name="Ω (scaled)" if row == 1 else None,
                       line=dict(color=c["OHM"], width=0.8, dash="longdash"),
                       opacity=0.6, showlegend=(row == 1)),
            row=row, col=1,
        )
    fig_t.update_layout(
        template=c["TMPL"], paper_bgcolor=c["BG"], plot_bgcolor=c["BG2"],
        font=dict(color=c["TXT"]),
        margin=dict(l=55, r=20, t=60, b=40),
        legend=dict(orientation="h", y=1.05, font=dict(size=10)),
    )
    fig_t.update_xaxes(title_text="time [ns]", row=3, col=1)

    # ── 3-D surface ───────────────────────────────────────────────────────────
    step = max(1, r.n_time // 60)
    fig_3d = go.Figure(go.Surface(
        x=r.t[::step], y=r.z, z=r.E[::step].T,
        colorscale="plasma", showscale=False,
    ))
    fig_3d.update_layout(
        template=c["TMPL"], paper_bgcolor=c["BG"],
        font=dict(color=c["TXT"]),
        scene=dict(
            xaxis_title="time [ns]", yaxis_title="z [mm]", zaxis_title="|E|",
            xaxis=dict(backgroundcolor=c["BG2"]),
            yaxis=dict(backgroundcolor=c["BG2"]),
            zaxis=dict(backgroundcolor=c["BG2"]),
        ),
        margin=dict(l=0, r=0, t=30, b=0),
    )

    # ── Control field ─────────────────────────────────────────────────────────
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(
        x=r.t_dense, y=r.rabi_profile, name="Ω(t)",
        line=dict(color=c["OHM"], width=2.5),
        fill="tozeroy", fillcolor="rgba(249,226,175,0.12)",
    ))
    fig_c.update_layout(
        template=c["TMPL"], paper_bgcolor=c["BG"], plot_bgcolor=c["BG2"],
        font=dict(color=c["TXT"]),
        title=dict(text="Control field  Ω(t)", font=dict(color=c["TTL"], size=13)),
        xaxis_title="time [ns]", yaxis_title="Rabi  Ω [GHz]",
        margin=dict(l=55, r=20, t=55, b=40),
    )

    # ── Metrics ───────────────────────────────────────────────────────────────
    metrics_txt = "\n".join([
        f"  Optical depth          OD  = {m.get('optical_depth', '?')}",
        f"  Group velocity         v_g = {m.get('group_velocity', '?'):.4g}  mm/ns",
        f"  Slow-down factor           = {m.get('slow_down_factor', '?'):.1f}×",
        f"  Storage efficiency     η   = {m.get('efficiency', '?'):.4f}",
        f"  Time delay                 = {m.get('time_delay', '?'):.3g}  ns",
        f"  Grid points  (z)           = {m.get('n_z', '?')}",
        f"  Time steps                 = {m.get('n_steps', '?')}",
        f"  Wall-clock time            = {m.get('run_time_s', '?')} s",
    ])

    # ── Spatial snapshots at 3 time points ────────────────────────────────────
    # Storage window: find when Ω ≈ 0
    thresh = r.rabi_profile.max() * 0.05
    store_mask = r.rabi_profile < thresh
    if store_mask.any():
        t_well_start = float(r.t_dense[np.argmax(store_mask)])
        t_well_end   = float(r.t_dense[len(r.t_dense) - np.argmax(store_mask[::-1]) - 1])
    else:
        t_well_start = r.t[len(r.t)//3]
        t_well_end   = r.t[2*len(r.t)//3]

    snap_times = {
        "Before storage":   t_well_start * 0.90,
        "Mid-storage":      (t_well_start + t_well_end) / 2,
        "Before retrieval": t_well_end * 1.02,
    }

    p_scale = 20

    fig_snaps = make_subplots(rows=1, cols=3,
                               subplot_titles=list(snap_times.keys()),
                               shared_yaxes=False)
    for col_i, (label, t_target) in enumerate(snap_times.items(), start=1):
        tidx = int(np.argmin(np.abs(r.t - t_target)))
        tidx = min(tidx, r.n_time - 1)

        fig_snaps.add_trace(
            go.Scatter(x=r.z, y=r.E[tidx], name="|E|" if col_i == 1 else None,
                       line=dict(color="#4682b4", width=2), showlegend=(col_i == 1)),
            row=1, col=col_i,
        )
        fig_snaps.add_trace(
            go.Scatter(x=r.z, y=r.S[tidx], name="|S|" if col_i == 1 else None,
                       line=dict(color="#e05555", width=2), showlegend=(col_i == 1)),
            row=1, col=col_i,
        )
        fig_snaps.add_trace(
            go.Scatter(x=r.z, y=r.P[tidx] * p_scale,
                       name=f"|P|×{p_scale}" if col_i == 1 else None,
                       line=dict(color=c["TXT"], width=1.2, dash="dash"),
                       showlegend=(col_i == 1)),
            row=1, col=col_i,
        )
        rabi_val = r.rabi_profile[min(int(r.t[tidx]/max(r.t_dense[1]-r.t_dense[0], 1e-9)),
                                       len(r.rabi_profile)-1)]
        fig_snaps.layout.annotations[col_i-1].update(
            text=f"{label}<br>t={r.t[tidx]:.1f} ns, Ω={rabi_val:.1f} GHz",
            font=dict(size=11),
        )
        # Medium shading
        fig_snaps.add_vrect(x0=m["enter"], x1=m["exit"],
                             fillcolor="rgba(80,200,80,0.08)", line_width=0,
                             row=1, col=col_i)
        fig_snaps.add_vline(x=m["enter"], line=dict(color=c["MED"], dash="dot", width=1),
                             row=1, col=col_i)
        fig_snaps.add_vline(x=m["exit"], line=dict(color=c["MED"], dash="dot", width=1),
                             row=1, col=col_i)

    fig_snaps.update_layout(
        template=c["TMPL"], paper_bgcolor=c["BG"], plot_bgcolor=c["BG2"],
        font=dict(color=c["TXT"], size=12),
        title=dict(text="Spatial field snapshots  (green = EIT medium)",
                   font=dict(color=c["TTL"], size=14), y=0.98),
        margin=dict(l=60, r=20, t=100, b=80),
        legend=dict(orientation="h", x=0.5, xanchor="center",
                    y=-0.18, yanchor="top", font=dict(size=11)),
    )
    fig_snaps.update_xaxes(title_text="z [mm]")
    fig_snaps.update_yaxes(title_text="|field|")

    return fig_t, fig_3d, fig_c, fig_snaps, metrics_txt


# 7. Draw animated spatial — also re-fires on speed or theme change
@app.callback(
    Output("plot-spatial", "figure"),
    Input("result-flag",       "data"),
    Input("theme-store",       "data"),
    Input("anim-speed-select", "value"),
    prevent_initial_call=True,
)
def _draw_spatial(flag, theme, speed_ms):
    r = _state.get("result")
    if r is None:
        return _empty_fig(theme or "dark",
                          "Run a simulation — spatial animation appears here.")
    c = _pal(theme or "dark")
    return _build_spatial_anim(r, c, int(speed_ms or 80))


# 8. Analytical parameter sweep
@app.callback(
    Output("plot-sweep", "figure"),
    Output("sweep-info", "children"),
    Input("btn-sweep", "n_clicks"),
    State("sweep-param",         "value"),
    State("sweep-metric",        "value"),
    State("sweep-min",           "value"),
    State("sweep-max",           "value"),
    State("sweep-pts",           "value"),
    State("sweep-logx",          "value"),
    State("sweep-overlay-param", "value"),
    State("sweep-overlay-vals",  "value"),
    State("params-store",        "data"),
    State("theme-store",         "data"),
    prevent_initial_call=True,
)
def _run_sweep(n_clicks, sweep_name, metric, x_min, x_max, n_pts,
               log_x, overlay_name, overlay_vals_str, params, theme):
    if not n_clicks:
        return no_update, no_update

    c = _pal(theme or "dark")
    p = params or _DEFAULTS
    n_pts = int(n_pts or 60)
    x_min = float(x_min or 1)
    x_max = float(x_max or 1000)
    log_x = bool(log_x)

    x_arr = (np.logspace(np.log10(max(x_min, 1e-9)), np.log10(x_max), n_pts)
             if log_x else np.linspace(x_min, x_max, n_pts))

    gamma_eg = 0.5 * (p["decay_e"] + p["dephase_e"])

    overlay_vals = []
    if overlay_name and overlay_name != "None":
        try:
            overlay_vals = [float(v.strip()) for v in overlay_vals_str.split(",") if v.strip()]
        except ValueError:
            pass

    SWEEP_KEY = {
        "Atom number N":   "N",
        "Control Rabi Ω": "Omega",
        "Medium length L": "L",
        "Storage time":    "storage_time",
    }
    XLABEL = {
        "Atom number N":   "N (atoms)",
        "Control Rabi Ω": "Ω [GHz]",
        "Medium length L": "L [cm]",
        "Storage time":    "Storage time [ns]",
    }
    YLABEL = {
        "efficiency":    "Storage efficiency η",
        "OD":            "Optical depth",
        "vg":            "Group velocity v_g [cm/ns]",
        "time_delay":    "Time delay [ns]",
        "eit_bandwidth": "EIT bandwidth [GHz]",
    }
    COLORS = [c["E"], c["P"], c["S"], c["OHM"], c["TTL"]]

    fig = go.Figure()

    def _compute(override: dict, label: str, color: str):
        q   = {**p, **override}
        geg = 0.5 * (q["decay_e"] + q["dephase_e"])
        gsg = 0.5 * q["dephase_s"]
        od0 = optical_depth(q["g"], q["N"], q["L"], q["c"], geg)
        if sweep_name == "Atom number N":
            data = sweep_N(x_arr, q["g"], q["L"], q["c"], geg, gsg, q["Omega"])
        elif sweep_name == "Control Rabi Ω":
            data = sweep_Omega(x_arr, q["N"], q["g"], q["L"], q["c"], geg, gsg)
        elif sweep_name == "Medium length L":
            data = sweep_L(x_arr, q["N"], q["g"], q["c"], geg, gsg, q["Omega"])
        elif sweep_name == "Storage time":
            data = sweep_storage_time(x_arr, od0, gsg, q["Omega"], geg)
        else:
            return
        y = data.get(metric, list(data.values())[-1])
        fig.add_trace(go.Scatter(x=x_arr, y=y, name=label,
                                 line=dict(color=color, width=2)))

    _compute({}, "baseline", COLORS[0])
    if overlay_vals:
        key = SWEEP_KEY.get(overlay_name, "")
        for i, val in enumerate(overlay_vals[:4]):
            _compute({key: val}, f"{overlay_name}={val}", COLORS[i + 1])

    fig.update_layout(
        template=c["TMPL"], paper_bgcolor=c["BG"], plot_bgcolor=c["BG2"],
        font=dict(color=c["TXT"]),
        title=dict(text=f"{YLABEL.get(metric, metric)} vs {sweep_name}",
                   font=dict(color=c["TTL"], size=13)),
        xaxis_title=XLABEL.get(sweep_name, sweep_name),
        yaxis_title=YLABEL.get(metric, metric),
        xaxis_type="log" if log_x else "linear",
        margin=dict(l=65, r=20, t=55, b=55),
        legend=dict(orientation="h", y=1.1),
    )

    od_base = optical_depth(p["g"], p["N"], p["L"], p["c"], gamma_eg)
    info = (f"Sweep: {sweep_name}  [{x_min:.3g} → {x_max:.3g}]  ({n_pts} pts)\n"
            f"Metric: {metric}\nBase OD = {od_base:.2f}")
    return fig, info


# 9. Theme toggle (clientside — toggles CSS class on <html>)
app.clientside_callback(
    """
    function(n_clicks, current) {
        if (!n_clicks) return window.dash_clientside.no_update;
        const next = (current === "dark") ? "light" : "dark";
        const root = document.documentElement;
        if (next === "light") root.classList.add("light-mode");
        else                  root.classList.remove("light-mode");
        return next;
    }
    """,
    Output("theme-store", "data"),
    Input("btn-theme", "n_clicks"),
    State("theme-store", "data"),
    prevent_initial_call=True,
)

# 10. Reset defaults — reload page
app.clientside_callback(
    """
    function(n) {
        if (!n) return window.dash_clientside.no_update;
        window.location.reload();
        return window.dash_clientside.no_update;
    }
    """,
    Output("params-store", "data", allow_duplicate=True),
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True,
)


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import webbrowser, threading as _th
    _th.Timer(1.5, lambda: webbrowser.open("http://localhost:8050")).start()
    app.run(debug=False, host="localhost", port=8050)
