"""Compare original and installed cartridge atlas coordinates."""
import bpy, json
import numpy as np
from pathlib import Path
O = Path(__file__).parent
S = O.parent / 'BenelliM4Super9020261006'
result = {}

def read_shells(label):
    rows = []
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or not ob.data.uv_layers:
            continue
        faces = list(ob.data.polygons)
        if not faces:
            continue
        for f in faces:
            groups = {ob.vertex_groups[g.group].name for vi in f.vertices for g in ob.data.vertices[vi].groups if g.weight > .5}
            if not groups.intersection({'WPN_root', 'WPN_Shell', 'WPN_Load', 'WPN_Trigger', 'WPN_bolt', 'Main', 'Shell', 'Load', 'Trigger', 'Slider'}):
                continue
            rows.append({'object': ob.name, 'material': ob.data.materials[f.material_index].name,
                         'groups': sorted(groups), 'area': f.area,
                         'p': [list(ob.matrix_world @ ob.data.vertices[vi].co) for vi in f.vertices],
                         'uv': [list(ob.data.uv_layers[0].data[li].uv) for li in f.loop_indices]})
    result[label] = rows

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O / 'Installed_Super90.fbx'), use_anim=False)
read_shells('installed')
bpy.ops.wm.open_mainfile(filepath=str(S / 'BenelliM4_Original_Editable.blend'))
read_shells('original')
(O / 'uv_inputs.json').write_text(json.dumps(result), encoding='utf-8')
for label, rows in result.items():
    print(label, 'shell faces', len(rows), 'groups', sorted({g for r in rows for g in r['groups']}))
print('SHELL_UV_INPUTS_SAVED', flush=True)
