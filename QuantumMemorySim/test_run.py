from protocols.eit.simulator import EITSimulator
sim = EITSimulator()
p = sim.default_params()
p['fast_mode'] = True
p['N'] = 50
p['storage_time'] = 20.0
result = sim.run(p, progress_callback=lambda x: None)
print('Run OK')
print('E shape:', result.E.shape)
print('E_real shape:', result.E_real.shape if result.E_real is not None else 'None')
print('S_real shape:', result.S_real.shape if result.S_real is not None else 'None')
print('Metrics:', {k: v for k, v in result.metrics.items() if k in ['optical_depth','efficiency','group_velocity']})
