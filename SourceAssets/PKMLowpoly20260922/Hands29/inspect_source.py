"""Read-only PKM source/export hand UV diagnosis; does not save the blend."""
import bpy
import json
import sys
from pathlib import Path

O = Path(__file__).parent
R = O.parent

def uv_summary(mesh, material_indices=None):
    loops = [i for p in mesh.polygons if material_indices is None or p.material_index in material_indices
             for i in p.loop_indices]
    result = []
    for layer in mesh.uv_layers:
        values = [tuple(layer.data[i].uv) for i in loops]
        result.append({'name': layer.name, 'active': layer == mesh.uv_layers.active,
                       'render': layer.active_render, 'loops': len(values),
                       'nonzero': sum(abs(u)+abs(v) > 1e-8 for u, v in values),
                       'range': [[min(v[j] for v in values), max(v[j] for v in values)]
                                 for j in range(2)] if values else []})
    return result

bpy.ops.wm.open_mainfile(filepath=str(R/'HandleFinish27/PKM_HandleFinish_Editable.blend'))
arms = bpy.data.objects['SK_Manny_Arms_Export']
report = {'source_hands': uv_summary(arms.data),
          'source_materials': [m.name for m in arms.data.materials],
          'part_layers': {o.name: [l.name for l in o.data.uv_layers]
                          for o in bpy.context.scene.objects if o.type == 'MESH' and 'mechanical_bone' in o}}
bpy.ops.wm.read_factory_settings(use_empty=True)
fixed = '--fixed' in sys.argv
fbx = (O if fixed else R/'HandleFinish27')/'Exports/SK_PKM_Manny_Modular.fbx'
bpy.ops.import_scene.fbx(filepath=str(fbx))
report['fbx_hands'] = []
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH':
        continue
    indices = {i for i,m in enumerate(ob.data.materials) if m and 'Manny' in m.name}
    if indices:
        report['fbx_hands'].append({'object': ob.name, 'slots': list(indices),
                                     'uv': uv_summary(ob.data, indices)})
(O/('corrected_uv_readback.json' if fixed else 'source_diagnosis.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PKM29_SOURCE', json.dumps({k:v for k,v in report.items() if k != 'part_layers'}), flush=True)
