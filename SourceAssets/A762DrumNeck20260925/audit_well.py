"""Assembled check: does the A762 drum's feed tower sit in the receiver's well?

The drum is placed the way the game places it (on the magazine socket), and its
clearance to the receiver is compared with the factory magazine's, which by
definition fits the well.
"""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
BANDS = [(0.030, 0.045), (0.045, 0.060), (0.060, 0.075), (0.075, 0.090), (0.090, 0.110)]

bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
sc = bpy.context.scene
print('MESH OBJECTS:')
for o in sorted(sc.objects, key=lambda x: x.name):
    if o.type == 'MESH':
        groups = [g.name for g in o.vertex_groups]
        print('  %-42s verts=%-6d parent=%-14s groups=%s' % (o.name, len(o.data.vertices),
              o.parent.name if o.parent else '-', groups[:4]), flush=True)

receiver = None
cands = [o for o in sc.objects if o.type == 'MESH' and o.parent == r
         and 'WPN_root' in [g.name for g in o.vertex_groups] and 'Before' not in o.name]
for o in cands:
    if 'Receiver' in o.name:
        receiver = o if receiver is None or len(o.data.vertices) > len(receiver.data.vertices) else receiver
if receiver is None and cands:
    receiver = max(cands, key=lambda o: len(o.data.vertices))
factory = [o for o in sc.objects if o.type == 'MESH' and o.name.startswith('A762_R02_Magazine_')]
print('receiver candidates:', [o.name for o in cands], flush=True)
print('receiver pick:', receiver.name if receiver else None, 'factory mag parts:', len(factory), flush=True)

rest = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
xf = rest.inverted() @ r.matrix_world.inverted()          # rest world -> magazine-bone rest frame
me = receiver.data
rev = [xf @ (receiver.matrix_world @ v.co) for v in me.vertices]
rep = [list(p.vertices) for p in me.polygons]
tree = BVHTree.FromPolygons(rev, rep, all_triangles=False)


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
fac_pts = []
for o in factory:
    fac_pts.extend(xf @ (o.matrix_world @ v.co) for v in o.data.vertices)
out['factory'] = probe('factory_mag  ', fac_pts)

with bpy.data.libraries.load(str(ACC / 'SM_A762_drum.blend'), link=False) as (src, dst):
    names = [n for n in src.objects]
    dst.objects = names
drum = [o for o in dst.objects if o is not None and o.type == 'MESH']
for o in drum:
    sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
drum_pts = []
for o in drum:
    drum_pts.extend(o.matrix_world @ v.co for v in o.data.vertices)
out['drum'] = probe('a762_drum    ', drum_pts)
(O / 'drum_well.json').write_text(json.dumps(out, indent=1))
print('DRUM_WELL_OK', flush=True)
