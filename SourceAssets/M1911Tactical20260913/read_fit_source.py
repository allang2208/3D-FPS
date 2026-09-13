"""Read current authoring geometry to place the reused devices on the pistol frame."""
import bpy, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent
S = O.parent
try:
    bpy.ops.wm.open_mainfile(filepath=str(S/'M1911Contact20260913/M1911_Contact_Editable.blend'))
except RuntimeError:
    if 'SK_M1911_Manny' not in bpy.data.objects:
        raise
rig = bpy.data.objects['SK_M1911_Manny']
root = rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local
frame = bpy.data.objects['M1911_Frame']
points = [root.inverted() @ frame.matrix_world @ v.co for v in frame.data.vertices]
surface = BVHTree.FromPolygons(points, [list(p.vertices) for p in frame.data.polygons])
samples = []
for y in [-.105, -.10, -.095, -.09, -.085, -.08, -.075, -.07, -.065, -.06, -.055, -.05, -.045, -.04]:
    row = {'y': y, 'underside': []}
    for x in [-.008, -.004, 0, .004, .008]:
        hit, normal, _, _ = surface.ray_cast(Vector((x, y, -.15)), Vector((0, 0, 1)), .25)
        row['underside'].append({'x': x, 'z': hit.z if hit else None})
    samples.append(row)
report = {'frame_underside_m': samples, 'devices': {}}
for kind, path in [('laser', S/'TacticalDevices20260913/M4/laser/Editable.blend'),
                   ('flashlight', S/'TacticalDevices20260913/HunyuanV3/M4/flashlight/Editable.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    ob = bpy.data.objects['SM_TacticalDevice']
    body = [v.co for p in ob.data.polygons if p.material_index == 0 for v in [ob.data.vertices[i] for i in p.vertices]]
    report['devices'][kind] = {'source': str(path), 'bounds_m': [[min(v[i] for v in body), max(v[i] for v in body)] for i in range(3)],
                               'slots': [m.name for m in ob.data.materials],
                               'emitter_m': list(bpy.data.objects['SOCKET_Emitter'].location)}
(O/'fit_source.json').write_text(json.dumps(report, indent=2))
print('M1911_TACTICAL_FIT_SOURCE_WRITTEN', flush=True)
