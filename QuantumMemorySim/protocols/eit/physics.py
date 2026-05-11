"""
EIT Maxwell-Bloch equations — numba-JIT compiled core.

Physics (Λ-system: |g⟩ ↔ |e⟩ ↔ |s⟩):
──────────────────────────────────────────
  (∂_t + c·∂_z) E = i·g·√N · P               [signal field, retarded frame]
  ∂_t P = −(γ_eg − iΔ₁)·P + i·g·√N·E + iΩ·S  [optical coherence ρ_ge]
  ∂_t S = −(γ_sg − iδ)·S + iΩ*·P             [spin-wave coherence ρ_gs]

Notation used in this module:
  Ng     = i·g·√N  (complex coupling, imaginary by convention)
  gamma1 = γ_eg − iΔ₁   (one-photon detuning absorbed into decay)
  gamma2 = γ_sg − iδ    (two-photon detuning)

Field propagation:
  The signal field propagates at c (speed of light).  Slow-light is NOT
  manually substituted — it emerges naturally from the Ng·P coupling term.
  This exactly matches the validated notebook (data() sets vg = c internally).
  The slow-light group velocity is used ONLY for timing calculations (when to
  switch off the control field) in simulator.py.

Spatial derivative:  4th-order centred finite differences (2nd-order at BCs).
Time integration:    RK4 (default) or RK2.

Validation vs existing notebook (EIT_NumericalAnalysis.ipynb):
  • Field equation uses c (not vg) — matches notebook's data() function.
  • np.conjugte typo fixed → np.conjugate.
  • prange parallelism preserved.
"""

from __future__ import annotations
import numpy as np
from numba import njit, prange


# ---------------------------------------------------------------------------
# Spatial gradient
# ---------------------------------------------------------------------------

@njit(fastmath=True, parallel=True)
def grad_4th(f: np.ndarray, dz: float) -> np.ndarray:
    """
    4th-order centred finite difference gradient.
    Interior: O(h⁴) stencil [-1, 8, 0, -8, 1] / 12h
    Boundaries: 2nd-order one-sided / centred stencils.
    """
    g = np.zeros_like(f)
    n = len(f)
    end = n - 1

    for i in prange(2, n - 2):
        g[i] = (-f[i + 2] + 8.0 * f[i + 1] - 8.0 * f[i - 1] + f[i - 2]) / (12.0 * dz)

    g[0]     = (-3.0 * f[0]   + 4.0 * f[1]   - f[2])                  / (2.0 * dz)
    g[1]     = (f[2]           - f[0])                                  / (2.0 * dz)
    g[end]   = (3.0 * f[end]  - 4.0 * f[end - 1] + f[end - 2])        / (2.0 * dz)
    g[end-1] = (f[end]         - f[end - 2])                           / (2.0 * dz)
    return g


# ---------------------------------------------------------------------------
# RHS functions for each field
# ---------------------------------------------------------------------------

@njit(fastmath=True)
def _rhs_E(E: np.ndarray, P: np.ndarray, Ng: np.ndarray,
           c: float, dz: float) -> np.ndarray:
    """dE/dt = Ng·P − c·∂_z E   (field propagates at c; slow-light emerges from Ng·P)"""
    return Ng * P - c * grad_4th(E, dz)


@njit(fastmath=True)
def _rhs_P(E: np.ndarray, P: np.ndarray, S: np.ndarray,
           Ng: np.ndarray, gamma1: complex,
           Rabi: complex) -> np.ndarray:
    """dP/dt = −γ₁·P + Ng·E + iΩ·S"""
    return -gamma1 * P + Ng * E + 1j * Rabi * S


@njit(fastmath=True)
def _rhs_S(P: np.ndarray, S: np.ndarray,
           gamma2: complex, Rabi: complex) -> np.ndarray:
    """dS/dt = −γ₂·S + iΩ*·P"""
    return -gamma2 * S + 1j * np.conjugate(Rabi) * P


# ---------------------------------------------------------------------------
# RK4 / RK2 single step
# ---------------------------------------------------------------------------

@njit(fastmath=True)
def rk4_step(
    E: np.ndarray, P: np.ndarray, S: np.ndarray,
    Ng: np.ndarray, c: float,
    gamma1: complex, gamma2: complex, Rabi: complex,
    dt: float, dz: float,
) -> tuple:
    """Single RK4 time step for the coupled Maxwell-Bloch system."""
    k1E = _rhs_E(E,             P,             Ng, c, dz)
    k1P = _rhs_P(E,             P,             S,             Ng, gamma1, Rabi)
    k1S = _rhs_S(P,             S,             gamma2, Rabi)

    h = dt / 2.0
    k2E = _rhs_E(E + h * k1E,  P + h * k1P,  Ng, c, dz)
    k2P = _rhs_P(E + h * k1E,  P + h * k1P,  S + h * k1S,  Ng, gamma1, Rabi)
    k2S = _rhs_S(P + h * k1P,  S + h * k1S,  gamma2, Rabi)

    k3E = _rhs_E(E + h * k2E,  P + h * k2P,  Ng, c, dz)
    k3P = _rhs_P(E + h * k2E,  P + h * k2P,  S + h * k2S,  Ng, gamma1, Rabi)
    k3S = _rhs_S(P + h * k2P,  S + h * k2S,  gamma2, Rabi)

    k4E = _rhs_E(E + dt * k3E, P + dt * k3P, Ng, c, dz)
    k4P = _rhs_P(E + dt * k3E, P + dt * k3P, S + dt * k3S, Ng, gamma1, Rabi)
    k4S = _rhs_S(P + dt * k3P, S + dt * k3S, gamma2, Rabi)

    w = dt / 6.0
    return (
        E + w * (k1E + 2.0 * k2E + 2.0 * k3E + k4E),
        P + w * (k1P + 2.0 * k2P + 2.0 * k3P + k4P),
        S + w * (k1S + 2.0 * k2S + 2.0 * k3S + k4S),
    )


@njit(fastmath=True)
def rk2_step(
    E: np.ndarray, P: np.ndarray, S: np.ndarray,
    Ng: np.ndarray, c: float,
    gamma1: complex, gamma2: complex, Rabi: complex,
    dt: float, dz: float,
) -> tuple:
    """Cheaper midpoint-rule (RK2) step — less accurate, faster."""
    k1E = _rhs_E(E, P, Ng, c, dz)
    k1P = _rhs_P(E, P, S, Ng, gamma1, Rabi)
    k1S = _rhs_S(P, S, gamma2, Rabi)
    h = dt / 2.0
    k2E = _rhs_E(E + h * k1E, P + h * k1P, Ng, c, dz)
    k2P = _rhs_P(E + h * k1E, P + h * k1P, S + h * k1S, Ng, gamma1, Rabi)
    k2S = _rhs_S(P + h * k1P, S + h * k1S, gamma2, Rabi)
    return E + dt * k2E, P + dt * k2P, S + dt * k2S


# ---------------------------------------------------------------------------
# Full time evolution (JIT compiled, called from simulator.py in a thread)
# ---------------------------------------------------------------------------

@njit(fastmath=True)
def time_evolve(
    E0: np.ndarray, P0: np.ndarray, S0: np.ndarray,
    z: np.ndarray,
    Ng: np.ndarray,
    c: float,
    gamma1: complex,
    gamma2: complex,
    rabi_profile: np.ndarray,
    dt: float,
    dz: float,
    n_steps: int,
    save_every: int,
    n_save: int,
    cut_frac: float,
    use_rk4: bool,
) -> tuple:
    """
    Full Maxwell-Bloch time evolution.

    Parameters
    ----------
    E0, P0, S0    : initial field arrays (complex128, length n_z)
    z             : spatial grid (real part used for display)
    Ng            : complex coupling array (i·g·√N, zero outside medium)
    c             : speed of light (field propagates at c; slow-light emerges from coupling)
    gamma1        : complex optical-coherence decay (γ_eg − iΔ₁)
    gamma2        : complex spin-wave decay       (γ_sg − iδ)
    rabi_profile  : control Rabi vs time (length n_steps)
    dt            : time step
    dz            : spatial step
    n_steps       : total number of time steps
    save_every    : record state every this many steps
    n_save        : pre-allocated number of save slots
    cut_frac      : fraction of z-array zeroed at left boundary each step
    use_rk4       : True → RK4, False → RK2

    Returns
    -------
    Es, Ps, Ss       : (n_save, n_z) saved field magnitude arrays |field|
    Es_r, Ps_r, Ss_r : (n_save, n_z) saved real-part arrays Re(field)
    ts               : (n_save,) time at each save slot
    """
    n_z = len(E0)
    cut_idx = int(n_z * cut_frac)

    Es = np.zeros((n_save, n_z), dtype=np.float64)
    Ps = np.zeros((n_save, n_z), dtype=np.float64)
    Ss = np.zeros((n_save, n_z), dtype=np.float64)
    Es_r = np.zeros((n_save, n_z), dtype=np.float64)
    Ps_r = np.zeros((n_save, n_z), dtype=np.float64)
    Ss_r = np.zeros((n_save, n_z), dtype=np.float64)
    ts = np.zeros(n_save, dtype=np.float64)

    E = E0.copy()
    P = P0.copy()
    S = S0.copy()

    save_idx = 0

    for step in range(n_steps):
        Rabi = rabi_profile[step] + 0j   # ensure complex for numba

        if use_rk4:
            E, P, S = rk4_step(E, P, S, Ng, c, gamma1, gamma2, Rabi, dt, dz)
        else:
            E, P, S = rk2_step(E, P, S, Ng, c, gamma1, gamma2, Rabi, dt, dz)

        # absorbing left boundary: zero out spurious reflections
        for i in range(cut_idx):
            E[i] = 0.0 + 0.0j
            P[i] = 0.0 + 0.0j
            S[i] = 0.0 + 0.0j

        if step % save_every == 0 and save_idx < n_save:
            # Save magnitudes: P is predominantly imaginary (Ng=i·g·√N coupling),
            # so P.real ≈ 0; |P| gives the physical envelope.
            Es[save_idx] = np.abs(E)
            Ps[save_idx] = np.abs(P)
            Ss[save_idx] = np.abs(S)
            Es_r[save_idx] = E.real
            Ps_r[save_idx] = P.real
            Ss_r[save_idx] = S.real
            ts[save_idx] = step * dt
            save_idx += 1

    return Es, Ps, Ss, Es_r, Ps_r, Ss_r, ts


# ---------------------------------------------------------------------------
# Group velocity (used in simulator setup)
# ---------------------------------------------------------------------------

def compute_group_velocity(c: float, Ng_max: complex, Rabi: float) -> complex:
    """
    v_g = c / (1 − (Ng/Ω)²)
    With Ng = i·g·√N, (Ng/Ω)² = −g²N/Ω², so denominator = 1 + g²N/Ω²  (real, >1).
    Result is real and positive for EIT slow-light regime.
    """
    if Rabi == 0:
        return 0.0 + 0.0j
    ratio = Ng_max / Rabi
    return c / (1.0 - ratio ** 2)
