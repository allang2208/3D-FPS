"""Where is the thumb relative to the magazine in the shipped AKM / A762 grip?

Reports, in the magazine's own rest frame, the contact of the thumb segments with
the shell and the tip's position, next to the accepted SVD / M4 grips.
"""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']


def eval_world(obj, dg):
    e = obj.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    verts = [M @ v.co for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return verts, polys


def run(label, path, action, f):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action if action is None else bpy.data.actions[action]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    sc = bpy.context.scene
    sc.frame_set(f); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    D = r.matrix_world @ pose['WPN_SOCKET_Magazine'] @ restb.inverted() @ r.matrix_world.inverted()
    mags = [o for o in sc.objects if o.type == 'MESH'
            and any(g.name == 'WPN_SOCKET_Magazine' for g in o.vertex_groups)]
    if not mags:
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        for o in dst.objects:
            if o is None:
                continue
            sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
            mags.append(o)
    # magazine meshes ride the carrier bone: rest world -> posed world through D
    mv, mp = [], []
    for m in mags:
        off = len(mv)
        mv.extend(D @ (m.matrix_world @ v.co) for v in m.data.vertices)
        mp.extend([[off + i for i in p.vertices] for p in m.data.polygons])
    tree = BVHTree.FromPolygons(mv, mp, all_triangles=False)
    av, _ = eval_world(arms, dg)
    groups = [g.name for g in arms.vertex_groups]
    e = arms.evaluated_get(dg); me = e.to_mesh()
    owner = []
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        owner.append(best)
    e.to_mesh_clear()
    out = {}
    for name in PARTS:
        idx = [i for i, o in enumerate(owner) if o == name]
        if not idx:
            continue
        d = []
        for i in idx:
            loc, nor, _, dist = tree.find_nearest(av[i])
            if loc is None:
                continue
            d.append(-dist if (av[i] - loc).dot(nor) < 0 else dist)
        d.sort()
        out[name] = {'min_mm': round(d[0] * 1000, 2), 'p05_mm': round(d[len(d) // 20] * 1000, 2),
                     'med_mm': round(d[len(d) // 2] * 1000, 2)}
    # magazine box in world, and thumb tip relative to its centre
    mn = Vector((min(p[i] for p in mv) for i in range(3)))
    mx = Vector((max(p[i] for p in mv) for i in range(3)))
    c = (mn + mx) / 2
    tip = r.matrix_world @ pose['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
    out['tip_rel_mag_centre_mm'] = [round(v * 1000, 1) for v in (tip - c)]
    out['mag_extent_mm'] = [round((mx[i] - mn[i]) * 1000, 1) for i in range(3)]
    print('%-6s f%-4s %s | tip %s' % (label, f, json.dumps({k: v for k, v in out.items() if k in PARTS}),
                                      out['tip_rel_mag_centre_mm']), flush=True)
    return out


V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
CASES = [
    ('AKM', V4 / 'AKM/standard/base/A_AKM_reload.blend', None, 148),
    ('A762', V4 / 'A762/standard/base/A_A762_reload.blend', None, 148),
    ('SVD', S / 'SVDThumbUp20260923/SVD_base_Editable.blend', 'A_SVD_reload', 148),
    ('M4', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', None, 76),
]
res = {}
for tag, p, a, f in CASES:
    res[tag] = run(tag, p, a, f)
(O / 'thumb_contact.json').write_text(json.dumps(res, indent=1))
print('THUMB_OK', flush=True)
