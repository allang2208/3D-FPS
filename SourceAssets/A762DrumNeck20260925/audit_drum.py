"""Measure the A762 drum's feed tower against the factory magazine.

All coordinates are the shared magazine-bone rest frame used by the accessories
and by the factory magazine mesh, so the three shapes can be compared directly:

* the donor AKM large drum as it was imported,
* the A762 drum that ships (the donor with its upper neck remapped),
* the A762 factory magazine, which by definition fits the magazine well.
"""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
DONOR = S / 'LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx'
SLICES = [0.020, 0.030, 0.040, 0.045, 0.050, 0.060, 0.070, 0.075, 0.080, 0.090]


def mesh_points(obj, xf=None):
    pts = []
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        pts.append(xf @ p if xf is not None else p)
    return pts


def report(label, points, tol=0.0025):
    out = {'n': len(points), 'slices': {}}
    for z in SLICES:
        row = [p for p in points if abs(p.z - z) <= tol]
        if len(row) < 4:
            out['slices'][z] = None
            continue
        xs = [p.x for p in row]; ys = [p.y for p in row]
        out['slices'][z] = {'n': len(row),
                            'cx': round(sum(xs) / len(xs) * 1000, 2), 'cy': round(sum(ys) / len(ys) * 1000, 2),
                            'dx': round((max(xs) - min(xs)) * 1000, 2),
                            'dy': round((max(ys) - min(ys)) * 1000, 2)}
    return out


res = {}
# donor AKM drum, as imported
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(DONOR))
pts = []
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        pts.extend(mesh_points(o))
res['donor_akm'] = report('donor', pts)

# shipped A762 drum
bpy.ops.wm.open_mainfile(filepath=str(ACC / 'SM_A762_drum.blend'), use_scripts=False)
pts = []
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        pts.extend(mesh_points(o))
res['a762_drum'] = report('a762', pts)

# A762 factory magazine, in the same magazine-bone rest frame
bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
rest = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
xf = rest.inverted() @ r.matrix_world.inverted()
pts = []
for o in bpy.context.scene.objects:
    if o.type == 'MESH' and o.name.startswith('A762_R02_Magazine_'):
        pts.extend(mesh_points(o, xf))
res['a762_factory_mag'] = report('factory', pts)
res['a762_factory_mag']['objects'] = [o.name for o in bpy.context.scene.objects
                                      if o.type == 'MESH' and o.name.startswith('A762_R02_Magazine_')]

for key in ('donor_akm', 'a762_drum', 'a762_factory_mag'):
    print('==', key, 'verts', res[key]['n'])
    for z, v in res[key]['slices'].items():
        print('   z=%5.0f mm  %s' % (z * 1000, json.dumps(v) if v else 'no section'), flush=True)
(O / 'drum_neck.json').write_text(json.dumps(res, indent=1))
print('DRUM_AUDIT_OK', flush=True)
