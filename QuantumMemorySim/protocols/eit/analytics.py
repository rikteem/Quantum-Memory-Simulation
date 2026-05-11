"""
Analytical / semi-analytical EIT formulas for fast parameter sweeps.

These avoid the ~minute-long full MB simulation for each sweep point and give
physically accurate scaling for OD >> 1.

References:
  Gorshkov et al., PRL 98, 123601 (2007)
  Fleischhauer & Lukin, PRL 84, 5094 (2000)
  Hammerer, Sørensen & Polzik, Rev. Mod. Phys. 82, 1041 (2010)
"""

from __future__ import annotations
import numpy as np


# ---------------------------------------------------------------------------
# Core EIT derived quantities
# ---------------------------------------------------------------------------

def group_velocity(c: float, g: float, N: int | float, Omega: float) -> float:
    """v_g = c·Ω² / (Ω² + g²·N)"""
    denom = Omega ** 2 + g ** 2 * N
    if denom == 0:
        return 0.0
    return c * Omega ** 2 / denom


def optical_depth(g: float, N: int | float, L: float,
                  c: float, gamma_eg: float) -> float:
    """OD = g²·N·L / (c·γ_eg)"""
    return g ** 2 * N * L / (c * gamma_eg)


def eit_linewidth(Omega: float, gamma_eg: float, od: float) -> float:
    """
    EIT transparency window half-linewidth (HWHM):
        Δω_EIT ≈ Ω² / (γ_eg · √OD)
    Valid for OD >> 1.
    """
    if od <= 0:
        return 0.0
    return Omega ** 2 / (gamma_eg * np.sqrt(od))


def storage_efficiency_adiabatic(od: float, gamma_sg: float,
                                 Omega: float, gamma_eg: float) -> float:
    """
    Adiabatic-transfer storage efficiency (Gorshkov 2007, Eq. 7):
        η ≈ [1 - 1/OD]²  · exp(-γ_sg/κ)
    where κ = Ω²/(γ_eg) is the EIT bandwidth parameter.

    This is a simplified upper bound ignoring retrieval losses.
    """
    if od <= 0:
        return 0.0
    kappa = Omega ** 2 / gamma_eg
    # Dark-state dephasing factor
    dephase = np.exp(-np.pi * gamma_sg / kappa) if kappa > 0 else 1.0
    return float(np.clip((1.0 - 1.0 / od) ** 2 * dephase, 0.0, 1.0))


def storage_efficiency_from_od(od: float) -> float:
    """
    Simplified efficiency η ≈ (1 - 1/OD)² for lossless spin wave.
    """
    if od <= 0:
        return 0.0
    return float(np.clip((1.0 - 1.0 / od) ** 2, 0.0, 1.0))


def time_delay(L: float, vg: float, c: float) -> float:
    """
    Group delay through medium: τ_delay = L/v_g − L/c
    """
    if vg == 0:
        return float("inf")
    return L / vg - L / c


def slow_down_factor(c: float, vg: float) -> float:
    """S = c/v_g"""
    if vg == 0:
        return float("inf")
    return c / vg


# ---------------------------------------------------------------------------
# Sweep helpers — return arrays for plotting
# ---------------------------------------------------------------------------

def sweep_N(
    N_range: np.ndarray,
    g: float, L: float, c: float, gamma_eg: float, gamma_sg: float, Omega: float,
) -> dict:
    """Sweep atom number N; return dict of result arrays."""
    od   = np.array([optical_depth(g, N, L, c, gamma_eg) for N in N_range])
    vg   = np.array([group_velocity(c, g, N, Omega) for N in N_range])
    eta  = np.array([storage_efficiency_adiabatic(o, gamma_sg, Omega, gamma_eg) for o in od])
    td   = np.array([time_delay(L, v, c) for v in vg])
    bw   = np.array([eit_linewidth(Omega, gamma_eg, o) for o in od])
    return {"N": N_range, "OD": od, "vg": vg, "efficiency": eta,
            "time_delay": td, "eit_bandwidth": bw}


def sweep_Omega(
    Omega_range: np.ndarray,
    N: int, g: float, L: float, c: float, gamma_eg: float, gamma_sg: float,
) -> dict:
    """Sweep control Rabi frequency Ω."""
    od   = optical_depth(g, N, L, c, gamma_eg)  # independent of Ω
    vg   = np.array([group_velocity(c, g, N, Om) for Om in Omega_range])
    eta  = np.array([storage_efficiency_adiabatic(od, gamma_sg, Om, gamma_eg)
                     for Om in Omega_range])
    td   = np.array([time_delay(L, v, c) for v in vg])
    bw   = np.array([eit_linewidth(Om, gamma_eg, od) for Om in Omega_range])
    return {"Omega": Omega_range, "OD": np.full_like(Omega_range, od),
            "vg": vg, "efficiency": eta, "time_delay": td, "eit_bandwidth": bw}


def sweep_L(
    L_range: np.ndarray,
    N: int, g: float, c: float, gamma_eg: float, gamma_sg: float, Omega: float,
) -> dict:
    """Sweep medium length L."""
    od  = np.array([optical_depth(g, N, L, c, gamma_eg) for L in L_range])
    vg  = group_velocity(c, g, N, Omega)
    eta = np.array([storage_efficiency_adiabatic(o, gamma_sg, Omega, gamma_eg) for o in od])
    td  = np.array([time_delay(L, vg, c) for L in L_range])
    bw  = np.array([eit_linewidth(Omega, gamma_eg, o) for o in od])
    return {"L": L_range, "OD": od, "vg": np.full_like(L_range, vg),
            "efficiency": eta, "time_delay": td, "eit_bandwidth": bw}


def sweep_temperature(
    T_range: np.ndarray,
    volume_m3: float,
    atom: str,
    g: float, L: float, c: float, gamma_eg: float, gamma_sg: float, Omega: float,
) -> dict:
    """Sweep cell temperature; compute N from vapour pressure."""
    from core.utils import atoms_in_volume
    N_arr = np.array([atoms_in_volume(T, volume_m3, atom) for T in T_range])
    od    = np.array([optical_depth(g, N, L, c, gamma_eg) for N in N_arr])
    vg    = np.array([group_velocity(c, g, N, Omega) for N in N_arr])
    eta   = np.array([storage_efficiency_adiabatic(o, gamma_sg, Omega, gamma_eg) for o in od])
    td    = np.array([time_delay(L, v, c) for v in vg])
    return {"T": T_range, "N": N_arr, "OD": od, "vg": vg,
            "efficiency": eta, "time_delay": td}


def sweep_storage_time(
    t_store_range: np.ndarray,
    od: float, gamma_sg: float, Omega: float, gamma_eg: float,
) -> dict:
    """
    Efficiency decay with storage time due to ground-state dephasing.
    η(t) ≈ η_0 · exp(−2·γ_sg·t)
    """
    eta_0 = storage_efficiency_adiabatic(od, 0.0, Omega, gamma_eg)
    eta   = eta_0 * np.exp(-2.0 * gamma_sg * t_store_range)
    return {"t_store": t_store_range, "efficiency": np.clip(eta, 0, 1)}


SWEEP_FUNCTIONS = {
    "Atom number N":       sweep_N,
    "Control Rabi Ω":      sweep_Omega,
    "Medium length L":     sweep_L,
    "Temperature T":       sweep_temperature,
    "Storage time":        sweep_storage_time,
}
