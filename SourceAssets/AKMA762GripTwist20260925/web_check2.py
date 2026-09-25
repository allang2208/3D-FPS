"""Extend the AKM / A762 thumb without touching the web.

The v2 pass swung the thumb root by 73-77 deg past the round-1 root to lay the
thumb along the magazine; that drags the skin between thumb and index, which is
what reads as a wrongly stretched web (measured: web gap +33 % against rest,
62 mm of web skin moved).

The SVD repair this project already accepted does the opposite - the root stays
within a few degrees of the base pose and the thumb extends because the two
distal segments are left almost straight.  So the candidates here keep the root
that is actually shipping (read from the round-1 blend at the grip frame, and
cross-checked against the round-1 receipt) and only change the distal flexion.

Measured per candidate:
  visible thumb   skin-centroid chain length, direction, angle to the magazine
  web gap         thumb_01 to index_01 skin-centroid distance vs the rest pose
  web movement    largest movement of any vertex weighted to thumb_01_l vs the
                  pose that is shipping now
  root swing      root rotation vs the shipping root
  pad             signed clearance to the posed magazine proxy
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
    'AKM': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
            O / 'AKM/standard/base/A_AKM_reload.blend'),
    'A762': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
             O / 'A762/standard/base/A_A762_reload.blend'),
}
RECEIPT = json.loads((O / 'authoring.json').read_text())
FIT = json.loads((O / 'thumb_fit.json').read_text())
V2 = json.loads((O / 'thumb_target2.json').read_text())
CANDIDATES = [('installed_flex43', 'installed', 4.0, 3.0),
              ('installed_flex00', 'installed', 0.0, 0.0),
              ('installed_flex86', 'installed', 8.0, 6.0),
              ('installed_as_shipped', 'installed', None, None),
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


def open_clip(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    act = r.animation_data.action
    r.animation_data.action_slot = act.slots[0]
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    return r, sc


def mag_tree(r, sc, gun, W, dg):
    D = W @ r.pose.bones['WPN_SOCKET_Magazine'].matrix @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ W.inverted()
    proxy = [o for o in sc.objects if o.type == 'MESH' and gun.upper() in o.name.upper() and 'MAG' in o.name.upper()]
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
    return BVHTree.FromPolygons(mv, mp, all_triangles=False), mag_arm


def sample(r, arms, tree, W):
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    cent = {p: [] for p in PARTS + WEB}
    webpts, pad = [], {p: [] for p in PARTS}
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
        if best in pad:
            loc, nor, _, dist = tree.find_nearest(p)
            if loc is not None:
                pad[best].append(-dist * 1000 if (p - loc).dot(nor) < 0 else dist * 1000)
    e.to_mesh_clear()
    return {'centroid': {k: sum(v, Vector()) / len(v) for k, v in cent.items() if v},
            'webpts': webpts,
            'pad': {k: round(min(v), 2) for k, v in pad.items() if v}}


def set_thumb(r, root, c, d, keep):
    for n, q in (('thumb_01_l', root),
                 ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                 ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep[n][0], q, keep[n][1])
    bpy.context.view_layer.update()


out = {}
for gun, (src, shipped) in CASES.items():
    # authoritative shipping root: read it from the round-1 blend
    r, sc = open_clip(shipped)
    q_inst = r.pose.bones['thumb_01_l'].matrix_basis.to_quaternion().copy()
    rec = Quaternion(RECEIPT['%s/standard/base/reload' % gun]['thumb_target']['thumb_01_l'])
    print('%s shipping root %s  (round-1 receipt %s, diff %.4f deg)'
          % (gun, [round(x, 5) for x in q_inst], [round(x, 5) for x in rec],
             math.degrees(q_inst.rotation_difference(rec).angle)), flush=True)
    # measurements run on the V4 source clip, which is the common source of all 30
    r, sc = open_clip(src)
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    W = r.matrix_world
    dg = bpy.context.evaluated_depsgraph_get()
    tree, mag_arm = mag_tree(r, sc, gun, W, dg)
    keep = {n: (lambda dd: (dd[0], dd[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    set_thumb(r, Quaternion(), 0.0, 0.0, keep)
    rest = sample(r, arms, tree, W)
    rest_gap = (rest['centroid']['thumb_01_l'] - rest['centroid']['index_01_l']).length * 1000
    rest_vis = (rest['centroid']['thumb_03_l'] - rest['centroid']['thumb_01_l'])
    p1 = FIT[gun]['params']
    set_thumb(r, q_inst, p1['c_02'], p1['d_03'], keep)
    now = sample(r, arms, tree, W)
    now_web = dict(now['webpts'])
    now_vis = (now['centroid']['thumb_03_l'] - now['centroid']['thumb_01_l'])
    print('%s shipping pose now: visible %.1f mm (%.1f%% of rest) at %.1f deg to the magazine, rise %+.1f mm, web gap %.2f mm (%.2f%% vs rest), pad %s'
          % (gun, now_vis.length * 1000, now_vis.length / rest_vis.length * 100,
             math.degrees(math.acos(max(-1, min(1, now_vis.normalized().dot(mag_arm))))),
             now_vis.z * 1000, (now['centroid']['thumb_01_l'] - now['centroid']['index_01_l']).length * 1000,
             (now['centroid']['thumb_01_l'] - now['centroid']['index_01_l']).length / (rest_gap / 1000) * 100 - 100,
             now['pad']), flush=True)
    q2 = Quaternion(V2[gun]['root_quat_wxyz'])
    rows = []
    for name, kind, c, d in CANDIDATES:
        if c is None:
            c, d = p1['c_02'], p1['d_03']
        root = {'installed': q_inst, 'rest': Quaternion(), 'v2': q2}[kind]
        set_thumb(r, root, c, d, keep)
        s = sample(r, arms, tree, W)
        vis = (s['centroid']['thumb_03_l'] - s['centroid']['thumb_01_l'])
        gap = (s['centroid']['thumb_01_l'] - s['centroid']['index_01_l']).length * 1000
        moved = max((p - now_web[i]).length * 1000 for i, p in s['webpts'])
        rows.append({'name': name, 'root': kind, 'c_02': c, 'd_03': d,
                     'root_swing_vs_shipping_deg': round(math.degrees(q_inst.rotation_difference(root).angle), 2),
                     'visible_len_mm': round(vis.length * 1000, 1),
                     'visible_vs_rest_pct': round(vis.length / rest_vis.length * 100, 1),
                     'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, vis.normalized().dot(mag_arm))))), 1),
                     'rise_mm': round(vis.z * 1000, 1),
                     'web_gap_mm': round(gap, 2),
                     'web_gap_vs_rest_pct': round(gap / (rest_gap / 1000) * 100 - 100, 2),
                     'web_skin_moved_vs_shipping_mm': round(moved, 2),
                     'pad_min_mm': s['pad'],
                     'root_quat_wxyz': [round(x, 6) for x in root]})
        print('   %-22s root_swing %6.2f  visible %5.1f mm (%5.1f%%)  angle %5.1f  rise %+7.1f  web_gap %+6.2f%%  web_skin_moved %6.2f mm  pad %s'
              % (name, rows[-1]['root_swing_vs_shipping_deg'], rows[-1]['visible_len_mm'],
                 rows[-1]['visible_vs_rest_pct'], rows[-1]['angle_to_mag_deg'], rows[-1]['rise_mm'],
                 rows[-1]['web_gap_vs_rest_pct'], rows[-1]['web_skin_moved_vs_shipping_mm'], s['pad']), flush=True)
    out[gun] = {'source': str(src), 'shipped_blend': str(shipped),
                'shipping_root_wxyz': [round(x, 6) for x in q_inst],
                'rest_web_gap_mm': round(rest_gap, 2),
                'rest_visible_len_mm': round(rest_vis.length * 1000, 1),
                'candidates': rows}
(O / 'thumb_web_check.json').write_text(json.dumps(out, indent=1))
print('WEB_CHECK_OK', flush=True)
