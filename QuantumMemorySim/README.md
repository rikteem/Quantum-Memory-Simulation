# Quantum Memory Simulator

A modular, GUI-based simulator for quantum memory protocols.  
Currently implements **EIT (Electromagnetically Induced Transparency)** memory via full Maxwell-Bloch equations. AFC and GEM are planned.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the GUI
python main.py
```

Requires Python ≥ 3.10. On first run, numba JIT-compiles the physics kernel (~5–15 s one-time cost).

---

## Project Structure

```
QuantumMemorySim/
├── main.py                      # Entry point
├── requirements.txt
├── README.md
├── core/
│   ├── constants.py             # Physical constants & vapour-pressure data
│   └── utils.py                 # Shared utility functions
├── protocols/
│   ├── base_protocol.py         # Abstract base class for all protocols
│   ├── eit/
│   │   ├── physics.py           # Maxwell-Bloch equations (numba JIT)
│   │   ├── pulses.py            # Signal & control field profiles
│   │   ├── simulator.py         # EIT simulation orchestrator
│   │   └── analytics.py        # Analytical formulas for fast parameter sweeps
│   ├── afc/                     # AFC protocol (coming soon)
│   └── gem/                     # GEM protocol (coming soon)
└── gui/
    ├── main_window.py           # QMainWindow with tab bar
    ├── tabs/
    │   ├── eit_tab.py           # EIT simulation panel
    │   ├── sweep_tab.py         # Parameter sweep panel
    │   ├── theory_tab.py        # Theory & background text
    │   └── placeholder_tab.py  # AFC / GEM placeholders
    └── widgets/
        ├── param_widgets.py     # Auto-building parameter input panel
        └── plot_canvas.py       # Matplotlib-in-Qt canvas + dark theme
```

---

## EIT Background

### The Λ-System

EIT quantum memory uses atoms with a **three-level Λ-structure**:

```
        |e⟩
       /   \
   g√N      Ω
     /         \
  |g⟩         |s⟩
```

- `|g⟩` — ground state, coupled to the **signal photon** via vacuum coupling `g`  
- `|e⟩` — excited state (decays at rate `γ_e`)  
- `|s⟩` — metastable state ("spin-wave" storage level, dephasing `γ_s`)  
- `Ω`   — classical **control field** Rabi frequency

### Maxwell-Bloch Equations

The coupled field–atom dynamics (slowly-varying envelope approximation):

```
(∂_t + c·∂_z) E  =  i·g·√N · P

∂_t P  =  −(γ_eg − iΔ₁) P  +  i·g·√N · E  +  iΩ · S

∂_t S  =  −(γ_sg − iδ) S  +  iΩ* · P
```

| Symbol    | Meaning                                        |
|-----------|------------------------------------------------|
| E         | Signal field envelope                          |
| P         | Optical coherence ρ_ge                         |
| S         | Spin-wave coherence ρ_gs                       |
| g         | Single-atom vacuum coupling (GHz)              |
| N         | Atom number                                    |
| Ω         | Control Rabi frequency (GHz)                   |
| γ_eg      | `(γ_decay + γ_dephase_e) / 2`                 |
| γ_sg      | `γ_dephase_s / 2`                              |
| Δ₁        | One-photon detuning                            |
| δ         | Two-photon (Raman) detuning Δ₁ − Δ₂           |

### EIT Slow Light

When Ω ≠ 0 and δ = 0, quantum interference creates a **transparency window** and dramatically reduces the group velocity:

```
v_g = c · Ω² / (Ω² + g²N)
```

For `Ω² ≪ g²N` (high optical depth), `v_g ≪ c` — the pulse is compressed inside the medium.

### Storage Protocol

1. **Write**: Signal enters with Ω on → slows to `v_g` inside ensemble  
2. **Store**: Ω switched off adiabatically → photon state maps to spin-wave S(z)  
3. **Read**: Ω switched back on → spin wave re-emits into signal mode  

### Optical Depth and Efficiency

```
OD = g²·N·L / (c·γ_eg)

η ≈ (1 − 1/OD)²    [lossless spin-wave limit]
```

Practical rule: OD > 10 gives η > 80%.

### EIT Bandwidth

```
Δω_EIT ≈ Ω² / (γ_eg · √OD)
```

The signal pulse bandwidth must fit within this window.

### Adiabaticity Condition

For faithful storage, the control-field ramp must satisfy:

```
|dΩ/dt| ≪ Ω² / γ_eg
```

---

## GUI Features

### EIT Simulation Tab
- Full Maxwell-Bloch simulation (RK4, numba JIT accelerated)
- All physics parameters configurable: N, g, Ω, L, detunings, decay rates
- **Five signal pulse shapes**: Gaussian, Square, sech², Lorentzian, tanh
- **Four plot views**: Spatial snapshot, Temporal evolution, 3-D surface, Control field profile
- Interactive time-slice slider for spatial plots
- Real-time metrics: OD, v_g, slow-down factor, efficiency, time delay

### Parameter Sweep Tab
- **Analytical sweeps** (instant): vary N, Ω, L, or storage time
- Plot any output metric: efficiency, OD, group velocity, time delay, EIT bandwidth
- **Overlay**: add a second parameter's variation as multiple curves
- Log-scale X-axis option

### Theory Tab
- Full EIT background with equations, tables, and references
- Covers: Λ-system, Maxwell-Bloch equations, slow light, storage protocol, OD, bandwidth, numerical methods

---

## Numerical Implementation Details

### Slow-Light Approximation
The field equation uses `v_g` instead of `c`, reducing the required spatial grid by a factor of `c/v_g`. This is valid in the EIT regime where the polariton propagates at `v_g`.

### Spatial Discretisation
4th-order centred finite differences (interior):
```
∂_z f[i] ≈ (−f[i+2] + 8f[i+1] − 8f[i−1] + f[i+2]) / (12 Δz)
```
2nd-order one-sided stencils at boundaries.

### CFL Stability
```
Δt ≤ Δz / c
```
Default: `dz = 0.004`, `dt = 0.005` → marginal stability. Reduce `dt` if fields develop oscillations.

---

## Validation Against Existing Notebook

The simulator was validated against `EIT/EIT_NumericalAnalysis.ipynb`:

| Check | Status |
|-------|--------|
| Maxwell-Bloch equations | ✅ Identical (phase convention preserved) |
| Group velocity formula `c/(1−(Ng/Ω)²)` | ✅ Correct: Ng imaginary → denominator = `1 + g²N/Ω²` |
| RK4 time integration | ✅ Identical 4-stage scheme |
| 4th-order spatial gradient | ✅ Same stencil |
| Detuning convention: `γ₁ = γ_eg − i(Δ₁+Δ₂)` | ✅ One-photon detuning correctly encoded |
| `np.conjugte` typo | ✅ Fixed → `np.conjugate` |
| Parallel numba (`prange`) | ✅ Preserved |

One intentional difference: the GUI simulator uses cleaner variable names and separates physics from orchestration, but the numerical kernel is equivalent.

---

## Adding a New Protocol (AFC, GEM, …)

1. Create `protocols/<name>/` directory with `__init__.py`
2. Subclass `BaseMemoryProtocol` (see `protocols/base_protocol.py`)
3. Implement `run()`, `default_params()`, `param_schema()`
4. Create a tab in `gui/tabs/<name>_tab.py`
5. Register the tab in `gui/main_window.py`

The `ParamPanel` widget auto-builds itself from `param_schema()`, so no extra widget code is needed for new parameters.

---

## References

1. Gorshkov, A. V. *et al.*, *Universal approach to optimal photon storage in atomic media*, **PRL 98**, 123601 (2007)  
2. Fleischhauer, M. & Lukin, M. D., *Dark-state polaritons in EIT*, **PRL 84**, 5094 (2000)  
3. Hammerer, K., Sørensen, A. S. & Polzik, E. S., *Quantum interfaces between light and atomic ensembles*, **Rev. Mod. Phys. 82**, 1041 (2010)  
4. Lukin, M. D., *Colloquium: Trapping and manipulating photon states in atomic ensembles*, **Rev. Mod. Phys. 75**, 457 (2003)  
5. Simon, C. *et al.*, *Quantum memories — a review*, **Eur. Phys. J. D 58**, 1 (2010)  
