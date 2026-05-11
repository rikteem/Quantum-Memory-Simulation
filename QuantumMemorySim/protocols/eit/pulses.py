"""
Signal pulse shapes and control-field (Rabi) temporal profiles for EIT memory.

All functions operate on pre-allocated NumPy arrays for speed.
"""

from __future__ import annotations
import numpy as np


# ---------------------------------------------------------------------------
# Spatial signal-pulse profiles  (returned as complex128 arrays)
# ---------------------------------------------------------------------------

def gaussian_pulse(z: np.ndarray, center: float, fwhm: float,
                   amplitude: float = 1.0) -> np.ndarray:
    """Gaussian signal pulse envelope."""
    sigma = fwhm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    return (amplitude / (sigma * np.sqrt(2.0 * np.pi))) * np.exp(
        -((z - center) ** 2) / (2.0 * sigma ** 2)
    ).astype(np.complex128)


def square_pulse(z: np.ndarray, z_start: float, z_end: float,
                 amplitude: float = 1.0) -> np.ndarray:
    """Rectangular (top-hat) signal pulse."""
    out = np.zeros(len(z), dtype=np.complex128)
    mask = (z >= z_start) & (z <= z_end)
    out[mask] = amplitude
    return out


def sech2_pulse(z: np.ndarray, center: float, fwhm: float,
                amplitude: float = 1.0) -> np.ndarray:
    """
    Hyperbolic-secant squared pulse: A·sech²((z-z₀)/τ).
    τ = FWHM / (2·arccosh(√2)).
    Optimal shape for many EIT-based memory schemes.
    """
    tau = fwhm / (2.0 * np.arccosh(np.sqrt(2.0)))
    arg = (z - center) / tau
    # clip to avoid overflow in cosh for large |arg|
    arg = np.clip(arg, -500, 500)
    return (amplitude * (1.0 / np.cosh(arg)) ** 2).astype(np.complex128)


def lorentzian_pulse(z: np.ndarray, center: float, fwhm: float,
                     amplitude: float = 1.0) -> np.ndarray:
    """Lorentzian (Cauchy) signal pulse."""
    gamma = fwhm / 2.0
    return (amplitude * gamma ** 2 / ((z - center) ** 2 + gamma ** 2)).astype(
        np.complex128
    )


def tanh_pulse(z: np.ndarray, center: float, rise: float,
               amplitude: float = 1.0) -> np.ndarray:
    """
    Smooth step-like pulse built from two tanh edges.
    `rise` controls edge sharpness (larger = sharper).
    """
    edge1 = (np.tanh( rise * (z - center + 1.0)) + 1.0) / 2.0
    edge2 = (np.tanh(-rise * (z - center - 1.0)) + 1.0) / 2.0
    return (amplitude * edge1 * edge2).astype(np.complex128)


def build_signal_pulse(
    z: np.ndarray,
    shape: str,
    enter: float,
    medium_length: float,
    fwhm: float = 2.0,
    amplitude: float = 1.0,
    c: float = 0.3,
    center_override: float | None = None,
) -> np.ndarray:
    """
    Factory that constructs the initial signal field over the spatial grid z.

    The pulse is centred at z=0 (or center_override) so it propagates into
    the medium (which starts at z=enter) at the speed of light.

    Parameters
    ----------
    z               : spatial grid array (real)
    shape           : 'gaussian' | 'square' | 'sech2' | 'lorentzian' | 'tanh'
    enter           : z-coordinate where medium begins
    medium_length   : length of the atomic ensemble
    fwhm            : pulse FWHM in spatial units
    amplitude       : peak amplitude
    c               : speed of light (working units)
    center_override : if given, use this as pulse center instead of auto-placement
    """
    sigma = fwhm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    center = center_override if center_override is not None else (enter - 4.0 * sigma)

    shape = shape.lower()
    if shape == "gaussian":
        return gaussian_pulse(z, center, fwhm, amplitude)
    elif shape == "square":
        return square_pulse(z, center - fwhm / 2.0, center + fwhm / 2.0, amplitude)
    elif shape == "sech2":
        return sech2_pulse(z, center, fwhm, amplitude)
    elif shape == "lorentzian":
        return lorentzian_pulse(z, center, fwhm, amplitude)
    elif shape == "tanh":
        return tanh_pulse(z, center, 2.0 / fwhm, amplitude)
    else:
        raise ValueError(f"Unknown pulse shape: {shape!r}")


# ---------------------------------------------------------------------------
# Temporal control-field (Rabi) profiles
# ---------------------------------------------------------------------------

def rabi_on_off_profile(
    t: np.ndarray,
    max_amplitude: float,
    storage_time: float,
    start_time: float,
    sharpness: float = 0.7,
) -> np.ndarray:
    """
    Build the temporal control-field Rabi profile that:
      1. Is ON (max_amplitude) while the signal enters the medium.
      2. Switches OFF to store the spin-wave.
      3. Switches back ON after `storage_time` to retrieve it.

    Parameters
    ----------
    t             : dense time array
    max_amplitude : peak Rabi frequency (GHz)
    storage_time  : dark time between switch-off and switch-on
    start_time    : time at which to begin the switch-off ramp
    sharpness     : 0–1 controlling ramp steepness (converted to tanh scale)
    """
    # Convert 0–1 sharpness to a usable tanh slope
    slope = 10.0 ** (-1.0 / (sharpness + 0.3))

    offset1 = np.arctanh(0.8) + start_time
    storage_start = offset1 - np.arctanh(-0.8)
    storage_end   = storage_start + storage_time
    offset2       = storage_end - np.arctanh(-0.8)

    edge1 = (np.tanh(-(t - offset1) * slope) + 1.0) / 2.0
    edge2 = (np.tanh( (t - offset2) * slope) + 1.0) / 2.0

    profile = edge1 + edge2
    profile -= np.min(profile)
    return (max_amplitude * profile).astype(np.float64)


def rabi_constant_profile(t: np.ndarray, amplitude: float) -> np.ndarray:
    """Constant (always-on) control field — EIT slow-light, no storage."""
    return np.full(len(t), amplitude, dtype=np.float64)


def rabi_gaussian_profile(
    t: np.ndarray,
    max_amplitude: float,
    center: float,
    fwhm: float,
) -> np.ndarray:
    """Gaussian-shaped control pulse."""
    sigma = fwhm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    return (max_amplitude * np.exp(-((t - center) ** 2) / (2.0 * sigma ** 2))).astype(
        np.float64
    )
