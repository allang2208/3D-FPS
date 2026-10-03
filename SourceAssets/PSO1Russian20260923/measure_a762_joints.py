"""Measure A762 PSO joint clearance. Read-only."""
import bpy, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))

def world_mesh(ob):
    mw = ob.matrix_world
    verts = [mw @ v.co for v in ob.data.vertices]
    faces = [tuple(p.vertices) for p in ob.data.polygons]
    return verts, faces, BVHTree.FromPolygons(verts, faces)

objs = {ob.name: ob for ob in bpy.context.scene.objects if ob.type == 'MESH' and not ob.hide_render}
trees = {}
verts = {}
for name, ob in objs.items():
    v, f, t = world_mesh(ob)
    verts[name] = v
    trees[name] = t

pairs = [
    ('A762_ContouredPad_0', 'A762_BridgeArm_0'),
    ('A762_ContouredPad_1', 'A762_BridgeArm_1'),
    ('A762_BridgeArm_0', 'A762_DovetailSpine'),
    ('A762_BridgeArm_1', 'A762_DovetailSpine'),
    ('A762_DovetailSpine', 'PSO_ScopeMount'),
    ('A762_RecoilStop', 'PSO_ScopeMount'),
    ('A762_ClampBolt_0', 'PSO_ScopeMount'),
    ('A762_ClampBolt_1', 'PSO_ScopeMount'),
    ('PSO_ScopeMount', 'PSO_ScopeBody'),
    ('PSO_ScopeBody', 'PSO_ScopeLens'),
    ('A762_BridgeArm_0', 'PSO_ScopeMount'),
    ('A762_BridgeArm_1', 'PSO_ScopeMount'),
]
rows = []
for a, b in pairs:
    if a not in trees or b not in trees:
        rows.append({'pair': [a, b], 'missing': True})
        continue
    dists = []
    for p in verts[a]:
        loc, normal, index, dist = trees[b].find_nearest(p)
        if loc is not None:
            dists.append(dist)
    dists.sort()
    rows.append({
        'pair': [a, b],
        'min_mm': round(dists[0] * 1000, 2) if dists else None,
        'p10_mm': round(dists[max(0, len(dists)//10)] * 1000, 2) if dists else None,
        'samples': len(dists),
    })

# Receiver is hidden. Rebuild its surface and measure pad clearance.
refs = [ob for ob in bpy.context.scene.objects if ob.type == 'MESH' and ob.hide_render]
rv, rf = [], []
for ob in refs:
    mw = ob.matrix_world
    base = len(rv)
    rv.extend(mw @ v.co for v in ob.data.vertices)
    rf.extend(tuple(base + i for i in p.vertices) for p in ob.data.polygons)
receiver = BVHTree.FromPolygons(rv, rf) if rf else None
pads = []
if receiver:
    for name in ('A762_ContouredPad_0', 'A762_ContouredPad_1'):
        ds = []
        for p in verts[name]:
            loc, normal, index, dist = receiver.find_nearest(p)
            if loc is not None:
                ds.append(dist)
        ds.sort()
        pads.append({'pad': name, 'min_mm': round(ds[0]*1000, 2), 'p10_mm': round(ds[len(ds)//10]*1000, 2)})

out = {'joints': rows, 'pads_to_receiver': pads, 'objects': sorted(objs)}
(O / 'inspect_akm_a762' / 'a762_joints.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('A762_JOINTS', json.dumps(out), flush=True)
