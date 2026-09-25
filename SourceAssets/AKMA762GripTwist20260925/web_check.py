"""Extend the AKM / A762 thumb without touching the web.

The v2 pass swung the thumb root by 105 / 116 deg to lay the thumb along the
magazine.  A root swing of that size drags the skin between the thumb and the
index finger, which is what reads as a wrongly stretched web.

The SVD repair this project already accepted does the opposite: its root stays a
few degrees from the base pose and the thumb extends because the two distal
segments are left almost straight.  So here the candidates keep the root-1 root
(the pose the user already accepted for the twist) and only change the distal
flexion.  Each candidate is measured for

  visible thumb      skin-centroid chain length, direction, angle to the magazine
  web gap            distance between the thumb_01 and index_01 skin centroids,
                     against the rest pose
  web movement       largest movement of any vertex weighted to thumb_01_l,
                     against the round-1 pose (how much web skin the change drags)
  root swing         rotation of the root against the round-1 root
  pad                signed clearance to the posed magazine
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
WEB = ['thumb_01_l', 'index_01_l', 'index_02_l']
FRAME = 148
CASES = {
    'AKM': S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
    'A762': S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
}
FIT = json.loads((O / 'thumb_fit.json').read_text())
TGT = json.loads((O / 'thumb_target2.json').read_text())
CANDIDATES = [('round1_shipped', 'round1', 30.0, 24.97),
              ('round1_flex43', 'round1', 4.0, 3.0),
              ('round1_flex00', 'round1', 0.0, 0.0),
              ('round1_flex86', 'round1', 8.0, 6.0),
              ('rest_root_flex43', 'rest', 4.0, 3.0),
              ('v2_swing_flex43', 'v2', 4.0, 3.0)]


def principal(points):
    c = sum(points, Vector()) / len(points)
    xx = xy = xz = yy = yz = zz = 0.0
    for p in points:
        d = p - c
        xx += d.x * d.x; xy += d.x * d.y; xz += d.x * d.z
        yy += d.y * d.y; yz += d.y * d.z; zz += d.z * d.z
    M = Matrix(((xx, xy, xz), (xy, yy, yz), (xz, yz, zz)))
    v = Vector((M[0][0], M[1][0], M[2][0]))
    for i in (1, 2):
        w = Vector((M[0][i], M[1][i], M[2][i]))
        if w.length > v.length:
            v = w
    return c, v.normalized()


def setup(gun, path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    W = r.matrix_world
    D = W @ r.pose.bones['WPN_SOCKET_Magazine'].matrix @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ W.inverted()
    proxy = [o for o in sc.objects if o.type == 'MESH' and gun.upper() in o.name.upper() and 'MAG' in o.name.upper()]
    dg = bpy.context.evaluated_depsgraph_get()
    apply_d = False
    if not proxy:
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        proxy = [o for o in dst.objects if o is not None]
        for o in proxy:
            sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
        apply_d = True
    mv, mp = [], []
    for o in proxy:
        if not apply_d and any(m.type == 'ARMATURE' for m in o.modifiers):
            e = o.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
            off = len(mv); mv.extend(M @ v.co for v in me.vertices)
            mp.extend([[off + i for i in p.vertices] for p in me.polygons]); e.to_mesh_clear()
        else:
            off = len(mv)
            mv.extend(D @ (o.matrix_world @ v.co) for v in o.data.vertices)
            mp.extend([[off + i for i in p.vertices] for p in o.data.polygons])
    mag_c_p, axis = principal(mv)
    if (r.pose.bones['WPN_root'].head - mag_c_p).dot(axis) < 0:
        axis = -axis
    mag_arm = (W.to_3x3().inverted() @ axis).normalized()
    return r, arms, sc, W, BVHTree.FromPolygons(mv, mp, all_triangles=False), mag_arm


def sample(r, arms, tree, W):
    """/per-group skin centroids, web vertices and pad clearance for the current pose."""
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    cent = {p: [] for p in PARTS + WEB}
    webpts = []
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        p = M @ v.co
        if best in cent:
            cent[best].append(p)
            if best == 'thumb_01_l':
                webpts.append((v.index, p))
    e.to_mesh_clear()
    out = {'centroid': {k: sum(v, Vector()) / len(v) for k, v in cent.items() if v},
           'webpts': webpts}
    d = {}
    for p in PARTS:
        dd = []
        e2 = arms.evaluated_get(dg); me2 = e2.to_mesh(); M2 = e2.matrix_world
        # clearance needs the thumb vertex positions only; reuse the centroid pass
        e2.to_mesh_clear()
        break
    return out


def clearances(r, arms, tree, W):
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
            if loc is not None:
                d.append(-dist * 1000 if (q - loc).dot(nor) < 0 else dist * 1000)
        d.sort()
        out[p] = round(d[0], 2)
    return out


def set_thumb(r, root, c, d, keep):
    for n, q in (('thumb_01_l', root),
                 ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                 ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep[n][0], q, keep[n][1])
    bpy.context.view_layer.update()


out = {}
for gun, path in CASES.items():
    r, arms, sc, W, tree, mag_arm = setup(gun, path)
    keep = {n: (lambda dd: (dd[0], dd[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    p1 = FIT[gun]['params']
    q1 = (Matrix.Rotation(math.radians(p1['a_z']), 4, 'Z').to_quaternion() @
          Matrix.Rotation(math.radians(p1['b_x']), 4, 'X').to_quaternion())
    q2 = Quaternion(TGT[gun]['root_quat_wxyz'])
    set_thumb(r, Quaternion(), 0.0, 0.0, keep)
    rest = sample(r, arms, tree, W)
    rest_gap = (rest['centroid']['thumb_01_l'] - rest['centroid']['index_01_l']).length * 1000
    rest_vis = (rest['centroid']['thumb_03_l'] - rest['centroid']['thumb_01_l'])
    set_thumb(r, q1, 30.0, 24.97, keep)
    r1 = sample(r, arms, tree, W)
    r1_web = dict(r1['webpts'])
    r1_vis = (r1['centroid']['thumb_03_l'] - r1['centroid']['thumb_01_l'])
    rows = []
    for name, root_kind, c, d in CANDIDATES:
        root = {'round1': q1, 'rest': Quaternion(), 'v2': q2}[root_kind]
        set_thumb(r, root, c, d, keep)
        s = sample(r, arms, tree, W)
        vis = (s['centroid']['thumb_03_l'] - s['centroid']['thumb_01_l'])
        gap = (s['centroid']['thumb_01_l'] - s['centroid']['index_01_l']).length * 1000
        moved = max(abs((p - r1_web[i]).length * 1000) for i, p in s['webpts'])
        root_swing = math.degrees(q1.rotation_difference(root).angle)
        cl = clearances(r, arms, tree, W)
        rows.append({'name': name, 'root': root_kind, 'c_02': c, 'd_03': d,
                     'root_swing_vs_round1_deg': round(root_swing, 2),
                     'visible_len_mm': round(vis.length * 1000, 1),
                     'visible_vs_rest_pct': round(vis.length / rest_vis.length * 100, 1),
                     'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, vis.normalized().dot(mag_arm))))), 1),
                     'rise_mm': round(vis.z * 1000, 1),
                     'web_gap_mm': round(gap, 2),
                     'web_gap_vs_rest_pct': round(gap / rest_gap * 100 - 100, 2),
                     'web_skin_moved_vs_round1_mm': round(moved, 2),
                     'pad_min_mm': cl,
                     'root_quat_wxyz': [round(x, 6) for x in root]})
        print('%-32s root_swing %6.2f  visible %5.1f mm (%5.1f%%)  angle %5.1f  rise %+7.1f  web_gap %+5.2f%%  web_skin_moved %5.2f mm  pad %s'
              % (name, rows[-1]['root_swing_vs_round1_deg'], rows[-1]['visible_len_mm'],
                 rows[-1]['visible_vs_rest_pct'], rows[-1]['angle_to_mag_deg'], rows[-1]['rise_mm'],
                 rows[-1]['web_gap_vs_rest_pct'], rows[-1]['web_skin_moved_vs_round1_mm'], cl), flush=True)
    out[gun] = {'path': str(path), 'rest_web_gap_mm': round(rest_gap, 2),
                'rest_visible_len_mm': round(rest_vis.length * 1000, 1),
                'round1_visible_len_mm': round(r1_vis.length * 1000, 1),
                'round1_angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, r1_vis.normalized().dot(mag_arm))))), 1),
                'candidates': rows}
(O / 'thumb_web_check.json').write_text(json.dumps(out, indent=1))
print('WEB_CHECK_OK', flush=True)
