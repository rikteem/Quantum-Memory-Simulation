"""
EIT quantum memory simulator — orchestrates physics, pulse generation, and metrics.

Usage (from Python):
    from protocols.eit.simulator import EITSimulator
    sim = EITSimulator()
    result = sim.run(params, progress_callback=lambda p: print(p))

Usage (from GUI thread):
    Worker thread calls sim.run(...) and emits results via Qt signals.
"""

from __future__ import annotations
import time
from typing import Any, Callable, Optional

import numpy as np

from protocols.base_protocol import BaseMemoryProtocol, SimulationResult
from protocols.eit.physics import time_evolve, compute_group_velocity
# NOTE: time_evolve uses c (not vg) for field propagation — slow-light emerges from coupling.
# compute_group_velocity is used ONLY for timing calculations (start_time, pulse_width_inside).
from protocols.eit.pulses import build_signal_pulse, rabi_on_off_profile
from core.utils import optical_depth, group_velocity, storage_efficiency


class EITSimulator(BaseMemoryProtocol):
    NAME = "EIT (Electromagnetically Induced Transparency)"
    DESCRIPTION = (
        "Simulates quantum memory via EIT in a Λ-system using the full "
        "Maxwell-Bloch equations (RK4 + numba JIT)."
    )

    # ------------------------------------------------------------------
    # Default parameters
    # ------------------------------------------------------------------

    def default_params(self) -> dict[str, Any]:
        return {
            # --- Medium / atoms ---
            "N":           100,       # number of atoms
            "g":           10.0,      # coupling constant (GHz)
            "L":           2.0,       # medium length (working units)
            # --- Detunings ---
            "delta1":      0.0,       # one-photon detuning  Δ₁ (GHz)
            "delta2":      0.0,       # two-photon detuning  δ  (GHz)
            # --- Decay / dephasing ---
            "decay_e":     50.0 / 3,  # excited-state spontaneous decay (GHz)
            "dephase_e":   0.0,       # excited-state pure dephasing (GHz)
            "dephase_s":   0.0005,    # ground-state dephasing (GHz)
            # --- Control field ---
            "Omega":       30.0,      # max Rabi frequency (GHz)
            "storage_time": 100.0,    # dark storage time (working time units)
            "rabi_sharpness": 0.7,    # switch sharpness 0–1
            # --- Signal pulse ---
            "pulse_shape": "gaussian",  # gaussian | square | sech2 | lorentzian | tanh
            "pulse_fwhm":  2.0,       # spatial FWHM of input pulse
            "pulse_amplitude": 1.0,
            # --- Numerics ---
            "c":           0.3,       # speed of light (working units)
            "dz":          0.004,     # spatial step
            "dt":          0.005,     # time step
            "save_every":  5,         # save state every N steps
            "use_rk4":     True,      # True → RK4, False → RK2
            "cut_frac":    0.1,       # left-boundary absorber fraction
            "fast_mode":   False,     # True → coarser grid (~4× faster)
        }

    # ------------------------------------------------------------------
    # Parameter schema for automatic GUI panel generation
    # ------------------------------------------------------------------

    def param_schema(self) -> list[dict]:
        return [
            # ---- Medium & Atoms ----
            dict(name="N",      label="Atom number N",     type="int",   min=1,    max=100000, step=10,    unit="atoms", group="Medium & Atoms", tooltip="Total number of atoms in the ensemble"),
            dict(name="g",      label="Coupling g",        type="float", min=0.01, max=200.0,  step=0.5,   decimals=3, unit="GHz",    group="Medium & Atoms", tooltip="Single-photon coupling constant"),
            dict(name="L",      label="Medium length L",   type="float", min=0.1,  max=20.0,   step=0.1,   decimals=2, unit="mm",     group="Medium & Atoms", tooltip="Length of the atomic ensemble"),
            # ---- Fields & Detunings ----
            dict(name="Omega",  label="Control Rabi Ω",    type="float", min=0.1,  max=500.0,  step=1.0,   decimals=2, unit="GHz",    group="Fields & Detunings", tooltip="Peak control-field Rabi frequency"),
            dict(name="delta1", label="One-photon det. Δ₁",type="float", min=-50,  max=50.0,   step=0.1,   decimals=3, unit="GHz",    group="Fields & Detunings", tooltip="Probe detuning from |g⟩→|e⟩ transition"),
            dict(name="delta2", label="Two-photon det. δ",  type="float", min=-10,  max=10.0,   step=0.01,  decimals=4, unit="GHz",    group="Fields & Detunings", tooltip="Two-photon (Raman) detuning"),
            # ---- Decay & Dephasing ----
            dict(name="decay_e",   label="Excited decay γ_e",  type="float", min=0,  max=200.0, step=0.5,  decimals=3, unit="GHz",  group="Decay & Dephasing", tooltip="Spontaneous decay rate of excited state"),
            dict(name="dephase_e", label="Excited dephase",    type="float", min=0,  max=10.0,  step=0.001,decimals=4, unit="GHz",  group="Decay & Dephasing", tooltip="Pure dephasing of excited state"),
            dict(name="dephase_s", label="Ground dephase γ_s", type="float", min=0,  max=1.0,   step=0.0001,decimals=5,unit="GHz",  group="Decay & Dephasing", tooltip="Ground-state decoherence rate"),
            # ---- Storage ----
            dict(name="storage_time",    label="Storage time",   type="float", min=1,   max=10000, step=5,   decimals=1, unit="ns",  group="Storage", tooltip="Dark storage time between write and read pulses"),
            dict(name="rabi_sharpness",  label="Switch sharpness",type="float", min=0.01,max=0.99, step=0.05, decimals=2, unit="",   group="Storage", tooltip="Control-field switch sharpness (0=soft, 1=sharp)"),
            # ---- Signal Pulse ----
            dict(name="pulse_shape",     label="Pulse shape",    type="choice", choices=["gaussian","square","sech2","lorentzian","tanh"], group="Signal Pulse", tooltip="Shape of the input signal field"),
            dict(name="pulse_fwhm",      label="Pulse FWHM",     type="float", min=0.1, max=20.0, step=0.1, decimals=2, unit="mm",  group="Signal Pulse", tooltip="Full-width at half-maximum of signal pulse"),
            dict(name="pulse_amplitude", label="Amplitude",      type="float", min=0.01,max=100.0,step=0.1, decimals=2, unit="",    group="Signal Pulse", tooltip="Peak amplitude of signal pulse"),
            # ---- Numerics ----
            dict(name="c",          label="Speed of light c",  type="float", min=0.01, max=30.0,  step=0.01, decimals=3, unit="mm/ns", group="Numerics", tooltip="Speed of light in working units"),
            dict(name="dz",         label="Spatial step dz",   type="float", min=0.001,max=0.1,   step=0.001,decimals=4, unit="mm",    group="Numerics", tooltip="Spatial grid resolution"),
            dict(name="dt",         label="Time step dt",      type="float", min=0.001,max=0.1,   step=0.001,decimals=4, unit="ns",    group="Numerics", tooltip="Time integration step (CFL: dt ≤ dz/c recommended)"),
            dict(name="save_every", label="Save every N steps",type="int",   min=1,    max=100,   step=1,    unit="",      group="Numerics", tooltip="Record state every N time steps"),
            dict(name="use_rk4",    label="Use RK4 (else RK2)",type="choice",choices=["True","False"],           group="Numerics", tooltip="RK4 is more accurate; RK2 is ~2× faster"),
            dict(name="fast_mode", label="Fast mode (2× coarser)", type="choice", choices=["False","True"], group="Numerics", tooltip="Fast: dz=0.008mm dt=0.010ns (~4× faster, less accurate)"),
        ]

    # ------------------------------------------------------------------
    # Main simulation entry point
    # ------------------------------------------------------------------

    def run(
        self,
        params: dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> SimulationResult:
        p = {**self.default_params(), **params}

        # Fast mode: use coarser grid for ~4× speedup
        if str(p.get("fast_mode", "False")) == "True":
            p = {**p, "dz": 0.008, "dt": 0.010}

        # ---------- derived decay rates ----------
        gamma_eg = 0.5 * (p["decay_e"] + p["dephase_e"])
        gamma_sg = 0.5 * p["dephase_s"]
        gamma1 = complex(gamma_eg, -(p["delta1"] + p["delta2"]))
        gamma2 = complex(gamma_sg, -p["delta2"])

        # ---------- medium coupling ----------
        Ng_val = 1j * p["g"] * np.sqrt(p["N"])   # scalar, used for vg and max of Ng array
        vg = compute_group_velocity(p["c"], Ng_val, p["Omega"])

        # ---------- spatial grid ----------
        # Match the original notebook layout: pulse placed at z=0, medium at z=enter.
        # Spatial extent: from -(4*sigma) to exit + 4*lim so the pulse and retrieval fit.
        dz   = p["dz"]
        fwhm = p["pulse_fwhm"]
        sigma_spatial = fwhm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
        lim   = sigma_spatial * 4.0           # half-width of pulse region outside medium

        enter  = lim                          # medium entrance (matches notebook: enter = lim)
        exit_  = enter + p["L"]              # medium exit

        z_real = np.arange(-lim, exit_ + lim, dz)   # matches notebook: total span = L + 3·lim
        z = z_real.astype(np.complex128)

        n_z = len(z_real)
        enter_idx = int(np.argmin(np.abs(z_real - enter)))
        exit_idx  = int(np.argmin(np.abs(z_real - exit_)))

        # ---------- medium profile ----------
        Ng = Ng_val * np.ones(n_z, dtype=np.complex128)
        Ng[:enter_idx] = 0.0
        Ng[exit_idx:]  = 0.0

        # ---------- time grid ----------
        # vg_real used only for timing (when to switch off control field).
        # The actual field propagates at c.
        vg_real = abs(vg.real) if vg.real != 0 else 1e-6
        pulse_width_outside = 2.0 * lim                          # spatial extent outside
        pulse_width_inside  = vg_real * (pulse_width_outside / p["c"])
        start_time = (pulse_width_outside / p["c"]) + (p["L"] / 2.0 - pulse_width_inside) / vg_real
        extra_time = p["L"] / (2.0 * vg_real)
        run_time = 1.5 * p["storage_time"] + start_time + extra_time

        dt = p["dt"]
        n_steps  = int(run_time / dt)
        save_every = p["save_every"]
        n_save = n_steps // save_every + 1

        t_dense = np.arange(0.0, n_steps * dt, dt)
        # Ensure rabi_profile has exactly n_steps entries
        rabi_profile = rabi_on_off_profile(
            t_dense[:n_steps], p["Omega"], p["storage_time"],
            start_time, p["rabi_sharpness"],
        )
        if len(rabi_profile) < n_steps:
            rabi_profile = np.pad(rabi_profile, (0, n_steps - len(rabi_profile)))

        # ---------- initial conditions ----------
        # Pulse centred at z=0 (left edge of grid = -lim, medium starts at lim)
        E0 = build_signal_pulse(z_real, p["pulse_shape"], enter,
                                p["L"], fwhm, p["pulse_amplitude"], p["c"],
                                center_override=0.0)
        P0 = np.zeros(n_z, dtype=np.complex128)
        S0 = np.zeros(n_z, dtype=np.complex128)

        # ---------- run (numba JIT) ----------
        if progress_callback:
            progress_callback(5)

        t0 = time.time()
        use_rk4 = p["use_rk4"] if isinstance(p["use_rk4"], bool) else (p["use_rk4"] == "True")

        Es, Ps, Ss, Es_r, Ps_r, Ss_r, ts = time_evolve(
            E0, P0, S0,
            z, Ng,
            float(p["c"]),   # field propagates at c; slow-light emerges from coupling
            gamma1, gamma2,
            rabi_profile.astype(np.float64),
            dt, dz,
            n_steps, save_every, n_save,
            p["cut_frac"],
            use_rk4,
        )
        elapsed = time.time() - t0

        if progress_callback:
            progress_callback(90)

        # ---------- strip empty trailing rows ----------
        nonzero = ~(Es == 0).all(axis=1)
        Es = Es[nonzero]
        Ps = Ps[nonzero]
        Ss = Ss[nonzero]
        ts = ts[nonzero]
        Es_r = Es_r[nonzero]
        Ps_r = Ps_r[nonzero]
        Ss_r = Ss_r[nonzero]

        # ---------- metrics ----------
        od = optical_depth(p["g"], p["N"], p["L"], p["c"], gamma_eg)
        vg_scalar = group_velocity(p["c"], p["g"], p["N"], p["Omega"])

        # Efficiency: compare output E² at exit vs input E² at entry
        E_in  = Es[:, max(0, enter_idx - 2)]
        E_out = Es[:, min(n_z - 1, exit_idx + 2)]
        eta   = storage_efficiency(E_in, E_out, save_every * dt)

        # Time delay: peak propagation delay through medium
        peak_in  = ts[np.argmax(np.abs(E_in))]  if E_in.max()  != 0 else 0.0
        peak_out = ts[np.argmax(np.abs(E_out))] if E_out.max() != 0 else 0.0
        t_delay  = peak_out - peak_in - p["L"] / p["c"]

        metrics = {
            "optical_depth":      round(od, 3),
            "group_velocity":     round(float(vg_scalar), 6),
            "slow_down_factor":   round(p["c"] / vg_scalar, 1) if vg_scalar > 0 else float("inf"),
            "efficiency":         round(float(eta), 4),
            "time_delay":         round(float(t_delay), 3),
            "run_time_s":         round(elapsed, 2),
            "n_steps":            n_steps,
            "n_z":                n_z,
            "enter_idx":          enter_idx,
            "exit_idx":           exit_idx,
            "enter":              float(enter),
            "exit":               float(exit_),
            "gamma_eg":           gamma_eg,
            "gamma_sg":           gamma_sg,
        }

        if progress_callback:
            progress_callback(100)

        return SimulationResult(
            E=Es, P=Ps, S=Ss,
            E_real=Es_r, P_real=Ps_r, S_real=Ss_r,
            z=z_real,
            t=ts,
            rabi_profile=rabi_profile,
            t_dense=t_dense[:n_steps],
            metrics=metrics,
            protocol="EIT",
        )
