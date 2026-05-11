"""Test _build_spatial_anim in isolation to find any errors."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocols.eit.simulator import EITSimulator
import numpy as np

sim = EITSimulator()
p = sim.default_params()
p['fast_mode'] = True
p['N'] = 100
p['storage_time'] = 30.0
print("Running simulation...")
r = sim.run(p, progress_callback=lambda x: None)
print(f"Done. E shape={r.E.shape}, E_real shape={r.E_real.shape if r.E_real is not None else None}")
print(f"t range: {r.t[0]:.2f} to {r.t[-1]:.2f}")
print(f"t_dense length: {len(r.t_dense)}, dt={r.t_dense[1]-r.t_dense[0]:.4f}")
print(f"rabi_profile length: {len(r.rabi_profile)}")

# Now try to build the animation figure
print("Building animation figure...")
import app_dash
c = app_dash._pal("dark")
try:
    fig = app_dash._build_spatial_anim(r, c, 80)
    print(f"OK! Frames: {len(fig.frames)}, traces: {len(fig.data)}")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
