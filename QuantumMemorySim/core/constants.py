"""
Physical constants and default unit conventions for the quantum memory simulator.

Unit system (unless overridden per protocol):
  - Time   : nanoseconds (ns)
  - Length : centimetres (cm)  [re-scaled so c ≈ 0.3 cm/ns]
  - Freq   : GHz
"""

# Speed of light in cm/ns  (c = 30 cm/ns → 0.3 when lengths in mm-ish units)
C_LIGHT = 0.3          # working units used by the EIT notebook

# Boltzmann constant (SI)
K_BOLTZMANN = 1.380649e-23   # J/K

# Planck's reduced constant (SI)
HBAR = 1.054571817e-34       # J·s

# Rb-87 D1-line parameters (approximate, for vapour-pressure helper)
RB87_WAVELENGTH_D1 = 795e-9          # m
RB87_WAVELENGTH_D2 = 780e-9          # m
RB87_DECAY_RATE_D1 = 2 * 3.14159 * 5.75e6   # rad/s  (natural linewidth)
RB87_DIPOLE_D1     = 2.537e-29       # C·m

# Cs-133 D1-line parameters
CS133_WAVELENGTH_D1 = 894e-9         # m
CS133_DECAY_RATE_D1 = 2 * 3.14159 * 4.56e6  # rad/s
CS133_DIPOLE_D1     = 3.000e-29      # C·m

# Vapour pressure fit coefficients (Antoine-like, P in Pa, T in K)
# log10(P_Pa) = A - B/T
VAPOUR_PRESSURE = {
    "Rb87": {"A": 15.88, "B": 4529.5, "T_min": 298, "T_max": 550},
    "Cs133": {"A": 15.90, "B": 4963.5, "T_min": 298, "T_max": 500},
}

# Protocol registry – populated by each protocol's __init__
PROTOCOLS: dict = {}
