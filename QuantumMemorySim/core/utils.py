"""Shared utility functions used across all protocols."""

import numpy as np
from core.constants import VAPOUR_PRESSURE, K_BOLTZMANN


# ---------------------------------------------------------------------------
# Vapour-pressure / atom-number helpers
# ---------------------------------------------------------------------------

def vapour_pressure(T_K: float, atom: str = "Rb87") -> float:
    """
    Return vapour pressure in Pa for the given atom species and temperature.
    Uses Antoine-like log10(P) = A - B/T fit valid for T in [T_min, T_max] K.
    """
    coeff = VAPOUR_PRESSURE[atom]
    T = np.clip(T_K, coeff["T_min"], coeff["T_max"])
    return 10 ** (coeff["A"] - coeff["B"] / T)


def number_density(T_K: float, atom: str = "Rb87") -> float:
    """Return number density n [m⁻³] from ideal-gas law n = P/(k_B T)."""
    P = vapour_pressure(T_K, atom)
    return P / (K_BOLTZMANN * T_K)


def atoms_in_volume(T_K: float, volume_m3: float, atom: str = "Rb87") -> float:
    """Total atom number N in a given interaction volume (m³)."""
    return number_density(T_K, atom) * volume_m3


# ---------------------------------------------------------------------------
# Pulse utilities
# ---------------------------------------------------------------------------

def fwhm_to_sigma(fwhm: float) -> float:
    """Convert FWHM to Gaussian sigma."""
    return fwhm / (2 * np.sqrt(2 * np.log(2)))


def sech2_width_from_fwhm(fwhm: float) -> float:
    """Return the characteristic width τ of sech²(t/τ) from FWHM."""
    return fwhm / (2 * np.arccosh(np.sqrt(2)))


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def storage_efficiency(E_in: np.ndarray, E_out: np.ndarray,
                       dt: float) -> float:
    """
    η = ∫|E_out|² dt / ∫|E_in|² dt
    Integrate over a 1-D time array using trapezoidal rule.
    """
    _trapz = getattr(np, "trapezoid", None) or np.trapz   # trapz removed in NumPy 2.0
    num = _trapz(np.abs(E_out) ** 2) * dt
    den = _trapz(np.abs(E_in) ** 2) * dt
    if den == 0:
        return 0.0
    return float(np.clip(num / den, 0.0, 1.0))


def optical_depth(g: float, N: int, L: float, c: float, gamma: float) -> float:
    """
    OD = g²·N·L / (c·γ)
    All quantities in consistent working units.
    """
    return (g ** 2) * N * L / (c * gamma)


def group_velocity(c: float, g: float, N: int, Omega: float) -> float:
    """
    v_g = c·Ω² / (Ω² + g²·N)   [EIT slow-light group velocity]
    """
    denom = Omega ** 2 + (g ** 2) * N
    if denom == 0:
        return 0.0
    return c * (Omega ** 2) / denom


def eit_bandwidth(Omega: float, gamma: float, od: float) -> float:
    """
    Δω_EIT ≈ Ω² / (γ · √OD)   [EIT transparency window half-width]
    """
    if od <= 0:
        return 0.0
    return (Omega ** 2) / (gamma * np.sqrt(od))
