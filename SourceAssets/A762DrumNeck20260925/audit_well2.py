"""Probe the A762 magazine well cavity and compare it with the factory magazine,
the shipped drum tower and the AKM donor tower, all in the magazine-bone rest
frame.  Rays are cast outward from the magazine axis so the cavity walls - not
some outer boss - are what gets measured.
"""
import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
DONOR = S / 'LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx'
ZS = [0.040, 0.045, 0.050, 0.055, 0.060, 0.065, 0.070, 0.075, 0.080, 0.090]


def slab(points, z, tol=0.002):
    row = [p for p in points if abs(p.z - z) <= tol]
    if len(row) < 4:
        return None
    return {'n': len(row),
            'x': [round(min(p.x for p in row) * 1000, 2), round(max(p.x for p in row) * 1000, 2)],
            'y': [round(min(p.y for p in row) * 1000, 2), round(max(p.y for p in row) * 1000, 2)]}


bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
sc = bpy.context.scene
rest = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
xf = rest.inverted() @ r.matrix_world.inverted()
recv = bpy.data.objects['A762_Receiver']
rev = [xf @ (recv.matrix_world @ v.co) for v in recv.data.vertices]
rep = [list(p.vertices) for p in recv.data.polygons]
tree = BVHTree.FromPolygons(rev, rep, all_triangles=False)

factory = [o for o in sc.objects if o.type == 'MESH' and o.name.startswith('A762_R02_Magazine_')]
fac = [xf @ (o.matrix_world @ v.co) for o in factory for v in o.data.vertices]

with bpy.data.libraries.load(str(ACC / 'SM_A762_drum.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
drum = [o for o in dst.objects if o is not None and o.type == 'MESH']
drum_pts = [o.matrix_world @ v.co for o in drum for v in o.data.vertices]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(DONOR))
donor_pts = [o.matrix_world @ v.co for o in bpy.context.scene.objects if o.type == 'MESH'
             for v in o.data.vertices]

print('z(mm)   | well cavity  -X..+X / -Y..+Y (mm)      | factory mag bbox        | drum tower bbox        | donor tower bbox')
out = {'slices': {}}
for z in ZS:
    fs = slab(fac, z)
    ds = slab(drum_pts, z)
    os_ = slab(donor_pts, z)
    if fs:
        origin = Vector(((fs['x'][0] + fs['x'][1]) / 2000.0, (fs['y'][0] + fs['y'][1]) / 2000.0, z))
    else:
        origin = Vector((0.0005, 0.040, z))
    span = {}
    for name, d in (('-X', Vector((-1, 0, 0))), ('+X', Vector((1, 0, 0))),
                    ('-Y', Vector((0, -1, 0))), ('+Y', Vector((0, 1, 0)))):
        loc, nor, idx, dist = tree.ray_cast(origin, d, 0.2)
        span[name] = None if loc is None else round((loc - origin).dot(d) * 1000, 2)
    out['slices'][z] = {'cavity': span, 'factory': fs, 'drum': ds, 'donor': os_}
    print('%5.0f  | %s | %s | %s | %s' % (
        z * 1000,
        ' '.join('%s=%s' % (k, ('--' if v is None else '%.1f' % v)) for k, v in span.items()),
        (str(fs['x']) + str(fs['y'])) if fs else '-',
        (str(ds['x']) + str(ds['y'])) if ds else '-',
        (str(os_['x']) + str(os_['y'])) if os_ else '-'), flush=True)
(O / 'well_cavity.json').write_text(json.dumps(out, indent=1))
print('WELL_OK', flush=True)
