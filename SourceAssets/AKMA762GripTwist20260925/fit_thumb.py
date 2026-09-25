"""Fit a natural opposed thumb for the AKM / A762 magazine grip.

The shipped grip rolls ``thumb_01_l`` about its own axis by about 67 deg and
points it away from the shell (thumb pad sits 12-15 mm off the magazine).  This
search keeps the palm, the four fingers, the wrist and the magazine track frozen
and only re-derives the three thumb rotations: the root is restricted to a
swing-only rotation (no twist about the thumb axis), the two distal segments keep
a light flexion, and the objective puts the pad close to the shell without
penetrating it.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']


def swing_only(q):
    q = q.copy(); q.normalize()
    a = Vector((0.0, 1.0, 0.0))
    p = a * Vector((q.x, q.y, q.z)).dot(a)
    if p.length < 1e-12:
        return q
    tw = 2.0 * math.atan2(p.length, q.w)
    if p.dot(a) < 0:
        tw = -tw
    return q @ Quaternion(a, tw).inverted()


def target_quats(par):
    a, b, c, d = par
    root = swing_only(Matrix.Rotation(math.radians(a), 4, 'Z').to_quaternion() @
                      Matrix.Rotation(math.radians(b), 4, 'X').to_quaternion())
    return {'thumb_01_l': root,
            'thumb_02_l': Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion(),
            'thumb_03_l': Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion()}


def setup(path, action, f):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action if action is None else bpy.data.actions[action]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    sc = bpy.context.scene
    sc.frame_set(f); bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    D = r.matrix_world @ pose['WPN_SOCKET_Magazine'] @ restb.inverted() @ r.matrix_world.inverted()
    mags = [o for o in sc.objects if o.type == 'MESH'
            and any(g.name == 'WPN_SOCKET_Magazine' for g in o.vertex_groups)]
    if not mags:
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        for o in dst.objects:
            if o is not None:
                sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
                mags.append(o)
    mv, mp = [], []
    for m in mags:
        off = len(mv)
        mv.extend(D @ (m.matrix_world @ v.co) for v in m.data.vertices)
        mp.extend([[off + i for i in p.vertices] for p in m.data.polygons])
    return r, arms, sc, BVHTree.FromPolygons(mv, mp, all_triangles=False), mv


def measure(r, arms, tree):
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    acc = {p: [] for p in PARTS}
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if best in acc:
            acc[best].append(M @ v.co)
    e.to_mesh_clear()
    out = {}
    for p, pts in acc.items():
        d = []
        for q in pts:
            loc, nor, _, dist = tree.find_nearest(q)
            if loc is None:
                continue
            d.append(-dist * 1000 if (q - loc).dot(nor) < 0 else dist * 1000)
        d.sort()
        out[p] = {'min': d[0], 'p05': d[len(d) // 20], 'med': d[len(d) // 2]}
    return out


def apply_target(r, quats, parents=None):
    for n, q in quats.items():
        pb = r.pose.bones[n]
        loc, _, scale = pb.matrix_basis.decompose()
        pb.matrix_basis = Matrix.LocRotScale(loc, q, scale)
    bpy.context.view_layer.update()


CASES = {
    'AKM': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend', None, 148),
    'A762': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend', None, 148),
}
result = {}
for gun, (path, act, f) in CASES.items():
    r, arms, sc, tree, mv = setup(path, act, f)
    base = {n: r.pose.bones[n].matrix_basis.to_quaternion() for n in PARTS}
    before = measure(r, arms, tree)
    print('%s shipped: %s' % (gun, json.dumps({k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in before.items()})), flush=True)
    print('%s shipped thumb basis %s' % (gun, {k: [round(x, 4) for x in q] for k, q in base.items()}), flush=True)
    mn = Vector((min(p[i] for p in mv) for i in range(3)))
    mx = Vector((max(p[i] for p in mv) for i in range(3)))
    mag_c = (mn + mx) / 2
    mag_size = mx - mn

    def cost(par):
        apply_target(r, target_quats(par))
        pr = measure(r, arms, tree)
        c = 0.0
        for k in ('thumb_02_l', 'thumb_03_l'):
            gap = pr[k]['med']
            c += min(max(gap, 0.0), 60.0) ** 2 * 1.0
            c += 4.0 * max(0.0, -pr[k]['min'] - 1.5) ** 2
        c += 0.5 * min(max(pr['thumb_01_l']['med'], 0.0), 60.0) ** 2
        c += 4.0 * max(0.0, -pr['thumb_01_l']['min'] - 1.5) ** 2
        a, b, cc, d = par
        c += 0.05 * (a * a + b * b) + 0.05 * max(0.0, cc - 35) ** 2 + 0.05 * max(0.0, d - 35) ** 2
        return c, pr

    best = (None, None, 1e18)
    for a in range(-45, 46, 15):
        for b in range(-45, 46, 15):
            for cc in (0, 10, 20, 30):
                for d in (0, 10, 20, 30):
                    v, pr = cost((a, b, cc, d))
                    if v < best[2]:
                        best = ((a, b, cc, d), pr, v)
    par = list(best[0])
    step = 7.0
    for _ in range(6):
        improved = True
        while improved:
            improved = False
            for i in range(4):
                for s in (-1, 1):
                    cand = list(par); cand[i] += s * step
                    cand[0] = max(-60, min(60, cand[0])); cand[1] = max(-60, min(60, cand[1]))
                    cand[2] = max(-10, min(60, cand[2])); cand[3] = max(-10, min(60, cand[3]))
                    v, pr = cost(cand)
                    if v < best[2] - 1e-9:
                        best = (tuple(cand), pr, v); par = cand; improved = True
        step *= 0.5
    print('%s best %s cost %.1f  %s' % (gun, [round(x, 1) for x in best[0]], best[2],
                                        json.dumps({k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in best[1].items()})), flush=True)
    # near-rest reference candidate
    apply_target(r, {'thumb_01_l': Quaternion(), 'thumb_02_l': Quaternion(),
                     'thumb_03_l': Matrix.Rotation(math.radians(4), 4, 'Z').to_quaternion()})
    rest_pr = measure(r, arms, tree)
    print('%s near-rest  %s' % (gun, json.dumps({k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in rest_pr.items()})), flush=True)
    result[gun] = {'path': str(path), 'frame': f, 'bounds_mm': [round(v * 1000, 1) for v in mag_size],
                   'shipped': before, 'best_params_zxcd': list(best[0]), 'best': best[1],
                   'near_rest': rest_pr,
                   'params': {'a_z': best[0][0], 'b_x': best[0][1], 'c_02': best[0][2], 'd_03': best[0][3]}}
(O / 'thumb_fit.json').write_text(json.dumps(result, indent=1))
print('THUMB_FIT_OK', flush=True)
