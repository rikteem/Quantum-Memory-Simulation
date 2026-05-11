import app_dash
cb = app_dash.app.callback_map
for k, v in cb.items():
    outputs = v.get('outputs', [])
    inputs = v.get('inputs', [])
    print(f'CB: {k[:80]}')
    print(f'  outs={len(outputs)}, ins={len(inputs)}')
