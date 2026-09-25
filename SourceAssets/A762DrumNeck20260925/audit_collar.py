"""Clearance of each drum tower variant to the A762 magazine-well collar, which is
the ring the tower actually passes through."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
DONOR = S / 'LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx'
BANDS = [(0.035, 0.050), (0.050, 0.060), (0.060, 0.070), (0.070, 0.080), (0.080, 0.095)]

bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
sc = bpy.context.scene
rest = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
xf = rest.inverted() @ r.matrix_world.inverted()
rings = [o for o in sc.objects if o.type == 'MESH' and 'MagwellCollar' in o.name]
print('collar objects:', [o.name for o in rings], flush=True)
tv, tp = [], []
for o in rings:
    off = len(tv)
    tv.extend(xf @ (o.matrix_world @ v.co) for v in o.data.vertices)
    tp.extend([[off + i for i in p.vertices] for p in o.data.polygons])
tree = BVHTree.FromPolygons(tv, tp, all_triangles=False)
bb = ([round(min(p[i] for p in tv) * 1000, 1) for i in range(3)],
      [round(max(p[i] for p in tv) * 1000, 1) for i in range(3)])
print('collar bbox mm:', bb, flush=True)


def probe(label, points):
    rows = {}
    for lo, hi in BANDS:
        sel = [p for p in points if lo <= p.z < hi]
        if not sel:
            rows['%d-%d' % (lo * 1000, hi * 1000)] = None
            continue
        d = []
        for p in sel:
            loc, nor, _, dist = tree.find_nearest(p)
            if loc is None:
                continue
            d.append(-dist * 1000 if (p - loc).dot(nor) < 0 else dist * 1000)
        d.sort()
        rows['%d-%d' % (lo * 1000, hi * 1000)] = {'n': len(d), 'min': round(d[0], 2),
                                                  'p05': round(d[len(d) // 20], 2),
                                                  'med': round(d[len(d) // 2], 2),
                                                  'pen': sum(1 for x in d if x < -0.5)}
    print(label, json.dumps(rows), flush=True)
    return rows


out = {}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(DONOR))
donor = [o.matrix_world @ v.co for o in bpy.context.scene.objects if o.type == 'MESH' for v in o.data.vertices]
out['donor'] = probe('donor    ', donor)
with bpy.data.libraries.load(str(O / 'SM_A762_drum.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
rebuilt = [o.matrix_world @ v.co for o in dst.objects if o is not None and o.type == 'MESH'
           for v in o.data.vertices]
out['rebuilt'] = probe('rebuilt  ', rebuilt)
with bpy.data.libraries.load(str(ACC / 'SM_A762_drum.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
shipped = [o.matrix_world @ v.co for o in dst.objects if o is not None and o.type == 'MESH'
           for v in o.data.vertices]
out['shipped'] = probe('shipped  ', shipped)
(O / 'collar_fit.json').write_text(json.dumps(out, indent=1))
print('COLLAR_OK', flush=True)
