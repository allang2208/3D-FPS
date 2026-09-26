"""Dump the Clearwater wave/optics parameter values as stored, for the zero-wave hunt.

Reads MI_ClearwaterWater's stored overrides and the master's VectorParameter/ScalarParameter
expression defaults. The H probe showed the 48-wave sum renders as exactly zero, so the
question is whether the data is zero ON DISK (authoring bug) or zero AT RUNTIME (pin/type
bug) -- this answers the first half.
"""
import json

import unreal as u

EAL = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary

MASTER = '/Game/Clearwater/M_ClearwaterWater'
MI = '/Game/Clearwater/MI_ClearwaterWater'

out = {'master_defaults': {}, 'instance_overrides': {}}

master = EAL.load_asset(MASTER)
if master is None:
    raise SystemExit('cannot load ' + MASTER)
for expr in MEL.get_material_expressions(master):
    cls = expr.get_class().get_name()
    if cls == 'MaterialExpressionVectorParameter':
        name = str(expr.get_editor_property('parameter_name'))
        v = expr.get_editor_property('default_value')
        out['master_defaults'][name] = [round(float(c), 6) for c in (v.r, v.g, v.b, v.a)]
    elif cls == 'MaterialExpressionScalarParameter':
        name = str(expr.get_editor_property('parameter_name'))
        out['master_defaults'][name] = round(float(expr.get_editor_property('default_value')), 6)

mi = EAL.load_asset(MI)
if mi is None:
    raise SystemExit('cannot load ' + MI)
parent = mi.get_editor_property('parent')
out['instance_parent'] = parent.get_path_name() if parent else None
# Scalar/vector overrides live in the instance's parameter arrays.
for prop in ('scalar_parameter_values', 'vector_parameter_values'):
    try:
        arr = mi.get_editor_property(prop)
    except Exception as exc:
        out['instance_overrides'][prop + '_unreadable'] = str(exc)
        continue
    for entry in arr:
        info = entry.get_editor_property('parameter_info')
        name = str(info.get_editor_property('name'))
        if prop.startswith('scalar'):
            v = entry.get_editor_property('parameter_value')
            out['instance_overrides'][name] = round(float(v), 6)
        else:
            v = entry.get_editor_property('parameter_value')
            out['instance_overrides'][name] = [round(float(c), 6)
                                               for c in (v.r, v.g, v.b, v.a)]

waves_master = {k: v for k, v in out['master_defaults'].items()
                if k.startswith('Wave') and isinstance(v, list)}
amps = [v[2] for v in waves_master.values()]
print('CLEARWATER DUMP ' + json.dumps({
    'master_wave_count': len(waves_master),
    'master_wave_amplitude_nonzero': sum(1 for a in amps if abs(a) > 1e-9),
    'master_wave_sample': dict(list(waves_master.items())[:3]),
    'instance_wave_overrides': sum(1 for k in out['instance_overrides']
                                   if k.startswith('Wave')),
    'instance_sample': {k: out['instance_overrides'][k]
                        for k in list(out['instance_overrides'])[:6]},
    'instance_parent': out['instance_parent'],
}), flush=True)
with open(r'D:/FPS3D/FPSGAME/Saved/ClearwaterProbes/params_dump.json', 'w') as f:
    json.dump(out, f, indent=1)
print('CLEARWATER DUMP OK full file: Saved/ClearwaterProbes/params_dump.json', flush=True)
