"""Refit the AKM / A762 magazine-grip thumb so it extends freely upwards.

The first pass fitted the thumb by proximity to the shell, which curled it (55 and
31 deg at the last two joints) until it read as retracted into the web.  Following
the accepted SVD grip - "the thumb extends naturally upwards, the last two segments
keep a light flexion" - the objective here is:

* the thumb axis (thumb_01 head -> thumb_03 tip) aligns with the magazine's own
  "up" direction (the insertion travel of the magazine);
* the last two joints stay nearly straight;
* no penetration into the shell, and the tip stays clear of the web between the
  thumb and the index;
* the root is a swing-only rotation (no twist about the thumb axis), as before.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
CASES = {
    'AKM': (V4 / 'AKM/standard/base/A_AKM_reload.blend', None, 148, 'AKM_FactoryMagazine_Preview'),
    'A762': (V4 / 'A762/standard/base/A_A762_reload.blend', None, 148, None),
}


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


def mag_points(r, sc, name):
    if name:
        o = bpy.data.objects.get(name)
        if o:
            return [o.matrix_world @ v.co for v in o.data.vertices]
    pts = []
    for o in sc.objects:
        if o.type == 'MESH' and o.name.startswith('A762_R02_Magazine_'):
            pts.extend(o.matrix_world @ v.co for v in o.data.vertices)
    if not pts:
        with bpy.data.libraries.load(str(ACC / 'A762_AccessoryReady_Editable.blend'), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        for o in dst.objects:
            if o is not None:
                sc.collection.objects.link(o); o.hide_set(False)
                pts.extend(o.matrix_world @ v.co for v in o.data.vertices)
    return pts


result = {}
for gun, (path, act, f, magname) in CASES.items():
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action if act is None else bpy.data.actions[act]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local

    def pose_of(frame):
        sc.frame_set(int(frame), subframe=frame % 1); bpy.context.view_layer.update()
        return {b.name: b.matrix.copy() for b in r.pose.bones}

    p_lo, p_hi = pose_of(43), pose_of(76)
    mag_up = ((r.matrix_world @ p_hi['WPN_SOCKET_Magazine'].translation) -
              (r.matrix_world @ p_lo['WPN_SOCKET_Magazine'].translation)).normalized()
    pose = pose_of(f)
    pts = mag_points(r, sc, magname)
    tree = BVHTree.FromPolygons(pts, [], all_triangles=False) if False else None

    def thumb_dir(P):
        head = r.matrix_world @ P['thumb_01_l'].translation
        tip = r.matrix_world @ P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
        return (tip - head).normalized(), head, tip

    d0, head0, tip0 = thumb_dir(pose)
    web = (r.matrix_world @ pose['thumb_01_l'].translation +
           r.matrix_world @ pose['index_01_l'].translation) / 2
    # shell surface for penetration checks: all magazine geometry in world
    mv, mp = [], []
    for o in sc.objects:
        if o.type == 'MESH' and (o.name.startswith('A762_R02_Magazine_') or o.name == 'AKM_FactoryMagazine_Preview'):
            off = len(mv)
            mv.extend(o.matrix_world @ v.co for v in o.data.vertices)
            mp.extend([[off + i for i in p.vertices] for p in o.data.polygons])
    if not mv:
        with bpy.data.libraries.load(str(ACC / 'A762_AccessoryReady_Editable.blend'), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        for o in dst.objects:
            if o is None:
                continue
            sc.collection.objects.link(o); o.hide_set(False)
            off = len(mv)
            mv.extend(o.matrix_world @ v.co for v in o.data.vertices)
            mp.extend([[off + i for i in p.vertices] for p in o.data.polygons])
    shell = BVHTree.FromPolygons(mv, mp, all_triangles=False)

    def measure():
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
        for p, pts_ in acc.items():
            d = []
            for q in pts_:
                loc, nor, _, dist = shell.find_nearest(q)
                if loc is None:
                    continue
                d.append(-dist * 1000 if (q - loc).dot(nor) < 0 else dist * 1000)
            d.sort()
            out[p] = {'min': d[0], 'med': d[len(d) // 2]}
        return out

    def apply(par):
        for n, q in target_quats(par).items():
            pb = r.pose.bones[n]
            loc, _, scale = pb.matrix_basis.decompose()
            pb.matrix_basis = Matrix.LocRotScale(loc, q, scale)
        bpy.context.view_layer.update()

    cur = measure()
    d0, head0, tip0 = thumb_dir(pose)
    cur_dir_err = math.degrees(math.acos(max(-1, min(1, d0.dot(mag_up)))))
    print('%s shipped: thumb-vs-mag angle %.1f deg  tip-web %.1f mm  pad %s' % (
        gun, cur_dir_err, (tip0 - web).length * 1000,
        {k.replace('_l', ''): {kk: round(vv, 1) for kk, vv in v.items()} for k, v in cur.items()}), flush=True)

    def cost(par):
        apply(par)
        P = {b.name: b.matrix.copy() for b in r.pose.bones}
        d, head, tip = thumb_dir(P)
        ang = math.degrees(math.acos(max(-1, min(1, d.dot(mag_up)))))
        pr = measure()
        c = ang * ang
        c += 0.25 * (par[2] ** 2 + par[3] ** 2)
        c += 0.04 * (par[0] ** 2 + par[1] ** 2)
        for k in ('thumb_02_l', 'thumb_03_l'):
            c += 25.0 * max(0.0, -pr[k]['min'] - 1.0) ** 2
        gap = (tip - web).length * 1000
        c += 0.6 * max(0.0, 42.0 - gap) ** 2
        return c, {'ang': round(ang, 1), 'tip_web_mm': round(gap, 1),
                   'pad': {k.replace('_l', ''): {kk: round(vv, 1) for kk, vv in v.items()}
                           for k, v in pr.items()}}

    best = (None, None, 1e18)
    for a_ in range(-60, 61, 10):
        for b_ in range(-60, 61, 10):
            for c_ in (0, 6, 12, 18):
                for d_ in (0, 6, 12, 18):
                    v, info = cost((a_, b_, c_, d_))
                    if v < best[2]:
                        best = ((a_, b_, c_, d_), info, v)
    par = list(best[0]); step = 6.0
    for _ in range(6):
        improved = True
        while improved:
            improved = False
            for i in range(4):
                for s in (-1, 1):
                    cand = list(par); cand[i] += s * step
                    cand[0] = max(-70, min(70, cand[0])); cand[1] = max(-70, min(70, cand[1]))
                    cand[2] = max(-5, min(30, cand[2])); cand[3] = max(-5, min(30, cand[3]))
                    v, info = cost(cand)
                    if v < best[2] - 1e-9:
                        best = (tuple(cand), info, v); par = cand; improved = True
        step *= 0.5
    print('%s best %s cost %.1f  %s' % (gun, [round(x, 1) for x in best[0]], best[2], json.dumps(best[1])), flush=True)
    result[gun] = {'params': {'a_z': best[0][0], 'b_x': best[0][1], 'c_02': best[0][2], 'd_03': best[0][3]},
                   'cost': best[2], 'info': best[1], 'shipped': {'angle_deg': round(cur_dir_err, 1),
                   'tip_web_mm': round((tip0 - web).length * 1000, 1)}}
(O / 'thumb_fit2.json').write_text(json.dumps(result, indent=1))
print('THUMB_FIT2_OK', flush=True)
