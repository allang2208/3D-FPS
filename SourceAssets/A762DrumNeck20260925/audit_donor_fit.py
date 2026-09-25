"""Would the untouched AKM donor tower fit the A762 well?

Places the donor drum on the A762 magazine socket (same seat the game uses) and
measures its clearance to the receiver, so we know how much of the shipped remap
was actually needed."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
DONOR = S / 'LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx'
BANDS = [(0.030, 0.045), (0.045, 0.055), (0.055, 0.065), (0.065, 0.075), (0.075, 0.090)]

bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
rest = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
xf = rest.inverted() @ r.matrix_world.inverted()
recv = bpy.data.objects['A762_Receiver']
rev = [xf @ (recv.matrix_world @ v.co) for v in recv.data.vertices]
tree = BVHTree.FromPolygons(rev, [list(p.vertices) for p in recv.data.polygons], all_triangles=False)


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
                                                  'med': round(d[len(d) // 2], 2),
                                                  'pen': sum(1 for x in d if x < -0.5)}
    print(label, json.dumps(rows), flush=True)
    return rows


out = {}
with bpy.data.libraries.load(str(ACC / 'SM_A762_drum.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
shipped = [o.matrix_world @ v.co for o in dst.objects if o is not None and o.type == 'MESH'
           for v in o.data.vertices]
out['shipped_tower'] = probe('shipped A762 drum', shipped)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(DONOR))
# the donor is authored in the same magazine-bone rest frame
donor = [o.matrix_world @ v.co for o in bpy.context.scene.objects if o.type == 'MESH'
         for v in o.data.vertices]
out['donor_tower'] = probe('untouched donor  ', donor)
(O / 'donor_fit.json').write_text(json.dumps(out, indent=1))
print('DONOR_FIT_OK', flush=True)
