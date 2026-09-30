"""Blender (background): weapon-surface masks for the A762 accessories with a unique UV0.

blender -b --factory-startup -P bake_accessories.py
Reads Bake/accessory_plan.json (mask == 'bake') and the ACC_* geometry dumps; bakes the same
channels as the gun (R convex edge, G cavity, B AO, A exposure) into UV0 at 1024 (2048 for
parts over 900 cm2), with the per-vertex occlusion densified to ~2 mm. Each accessory is
baked alone (static mesh on its own; the gun is not an occluder). Writes
Bake/Accessories/T_A762_<acc>_WS_Mask.png and Bake/accessory_bake_report.json.
"""
import json
import sys
from pathlib import Path
import bpy
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import bake_a762 as B  # noqa: E402

plan = json.loads((HERE / 'Bake' / 'accessory_plan.json').read_text(encoding='utf-8'))
OUT = HERE / 'Bake' / 'Accessories'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = B.setup_cycles()
report = {}
for mesh, entry in plan.items():
    if entry['mask'] != 'bake' or not any(d['action'] == 'preset' for d in entry['slots'].values()):
        continue
    key = 'ACC_' + mesh.replace('SM_A762_', '')
    ob, header, _ = B.build_object(key, np.zeros(3))
    for other in scene.objects:
        other.hide_render = other is not ob
    dens = B.densify(ob)
    vp = B.vertex_masks(ob)
    res = 2048 if entry['uv0']['area_cm2'] > 900 else 1024
    image = bpy.data.images.new(key + '_bake', res, res, alpha=True, float_buffer=True)
    image.colorspace_settings.name = 'Non-Color'
    B.bake(ob, image, 'UV0')
    name = 'T_A762_%s_WS_Mask' % mesh.replace('SM_A762_', '')
    report[mesh] = {'texture': name, 'resolution': res, 'densified': dens, 'vertex_pass': vp,
                    'mask': B.finish(image, OUT / (name + '.png'))}
    print('A762_ACC_BAKED', mesh, json.dumps(report[mesh]['mask']), flush=True)
    bpy.data.objects.remove(ob)
    bpy.data.images.remove(image)
(HERE / 'Bake' / 'accessory_bake_report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
print('A762_ACC_BAKE_DONE', len(report), flush=True)
