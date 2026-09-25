"""Aim the AKM / A762 thumb up along the magazine with a nearly straight chain.

Round 1 fitted root swing + distal flexion jointly against pad clearance and
produced a thumb whose head->tip chord is only 33.6 mm of its 75 mm length: the
thumb curls into the web.  The accepted SVD thumb is 63.6 mm (85 %) and nearly
straight.  Here the root is solved by aiming the thumb chord at the magazine's
own long axis (principal axis of the posed magazine proxy, signed toward the
feed end), with the twist about the thumb's own +Y held at zero and only light
flexion in the last two segments.

Clean magazine proxy per gun: the mag-named mesh skinned to WPN_SOCKET_Magazine
(AKM: AKM_FactoryMagazine_Preview; SVD: SM_SVD_Magazine) or the A762 magazine
library part, posed with the magazine track.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
HAND_BONES = ['index_01_l', 'index_02_l', 'index_03_l', 'middle_01_l', 'middle_02_l', 'middle_03_l',
              'ring_01_l', 'ring_02_l', 'ring_03_l', 'pinky_01_l', 'pinky_02_l', 'pinky_03_l', 'hand_l']
FLEXIONS = ((4.0, 3.0), (8.0, 6.0))
TILTS = (-30.0, -25.0, -20.0, -15.0, -10.0, -5.0, 0.0, 5.0, 10.0, 20.0, 30.0)
CASES = {
    'AKM': S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
    'A762': S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
}
FRAME = 148
FIT = json.loads((O / 'thumb_fit.json').read_text())


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


def twist_deg(q):
    q = q.copy(); q.normalize()
    a = Vector((0.0, 1.0, 0.0))
    p = a * Vector((q.x, q.y, q.z)).dot(a)
    if p.length < 1e-12:
        return 0.0
    return math.degrees(2.0 * math.atan2(p.length, q.w)) * (1.0 if p.dot(a) >= 0 else -1.0)


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


def tree_from(pts, polys):
    return BVHTree.FromPolygons(pts, polys, all_triangles=False)


def setup(gun, path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    W = r.matrix_world
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    D = W @ pose['WPN_SOCKET_Magazine'] @ restb.inverted() @ W.inverted()
    proxy = [o for o in sc.objects if o.type == 'MESH' and gun.upper() in o.name.upper() and 'MAG' in o.name.upper()]
    apply_d = False
    if not proxy:
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        proxy = [o for o in dst.objects if o is not None]
        for o in proxy:
            sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
        apply_d = True
    dg = bpy.context.evaluated_depsgraph_get()
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
    print('%s mag proxy %s (%d verts, posed=%s)' % (gun, [o.name for o in proxy], len(mv), not apply_d), flush=True)
    # hand geometry (left, no thumb) for thumb-vs-finger clearance
    e = arms.evaluated_get(dg); me = e.to_mesh(); AM = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    hv, hp = [], []
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if best in HAND_BONES:
            hv.append(AM @ v.co)
    for p in me.polygons:
        pass
    e.to_mesh_clear()
    hpoly = []
    return r, arms, sc, W, D, mv, mp, hv, hpoly


def pose_matrices(r):
    return {b.name: b.matrix.copy() for b in r.pose.bones}


def apply_root(r, q, c, d, keep):
    for n, qq in (('thumb_01_l', q),
                  ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                  ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
        pb = r.pose.bones[n]
        loc, scale = keep.get(n, (Vector(), Vector((1, 1, 1))))
        pb.matrix_basis = Matrix.LocRotScale(loc, qq, scale)
    bpy.context.view_layer.update()


def chord_of(r, W):
    P = pose_matrices(r)
    head = P['thumb_01_l'].translation
    tip = P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
    return head, tip, tip - head


def measure(r, arms, tree_mag, tree_hand, W):
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
        d, h = [], []
        for q in pts:
            loc, nor, _, dist = tree_mag.find_nearest(q)
            if loc is not None:
                d.append(-dist * 1000 if (q - loc).dot(nor) < 0 else dist * 1000)
            if tree_hand is not None:
                loc2, _, _, dist2 = tree_hand.find_nearest(q)
                if loc2 is not None:
                    h.append(dist2 * 1000)
        d.sort(); h.sort()
        out[p] = {'min': round(d[0], 2) if d else None, 'med': round(d[len(d) // 2], 2) if d else None,
                  'hand_min': round(h[0], 2) if h else None}
    return out


out = {}
for gun, path in CASES.items():
    r, arms, sc, W, D, mv, mp, hv, hpoly = setup(gun, path)
    tree_mag = tree_from(mv, mp)
    mag_c_p, axis = principal(mv)
    Wr = W.to_3x3()
    # sign the axis toward the receiver / feed end
    anchor = (r.pose.bones['WPN_root'].head if 'WPN_root' in r.pose.bones
              else r.pose.bones['hand_r'].matrix.translation)
    if (anchor - mag_c_p).dot(axis) < 0:
        axis = -axis
    mag_c = Wr.inverted() @ mag_c_p
    mag_arm = (Wr.inverted() @ axis).normalized()
    # hand-only geometry tree (built from the armature's evaluated mesh, left bones)
    e = arms.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = e.to_mesh(); AM = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    lv, lp, vmap = [], [], {}
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if best and best.endswith('_l') and best not in PARTS:
            vmap[v.index] = len(lv); lv.append(AM @ v.co)
    for p in me.polygons:
        idx = [vmap[i] for i in p.vertices if i in vmap]
        if len(idx) >= 3:
            lp.append(idx)
    e.to_mesh_clear()
    tree_hand = tree_from(lv, lp) if lv and lp else None
    # base pose (clip's shipped thumb) reference
    keep = {}
    for n in PARTS:
        loc, _, scale = r.pose.bones[n].matrix_basis.decompose()
        keep[n] = (loc, scale)
    for n in PARTS:
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep[n][0], Quaternion(), keep[n][1])
    bpy.context.view_layer.update()
    P = pose_matrices(r)
    head0 = P['thumb_01_l'].translation
    tip0 = P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
    rest_chord = (tip0 - head0).length * 1000
    M0 = P['thumb_01_l'].copy()
    d_rest = (M0.to_3x3() @ Vector((0, 1, 0))).normalized()
    # palm-side direction, for the tilt axis
    palm = r.pose.bones['hand_l'].matrix.translation
    v = palm - mag_c
    v_perp = (v - v.project(mag_arm))
    if v_perp.length < 1e-6:
        v_perp = Vector((1, 0, 0)) - Vector((1, 0, 0)).project(mag_arm)
    v_perp.normalize()
    tilt_axis = mag_arm.cross(v_perp).normalized()
    print('%s: mag proxy centre %s, long axis armature %s, rest chord %.1f mm of %.1f mm, palm-side %s'
          % (gun, [round(x * 1000, 1) for x in mag_c_p], [round(x, 3) for x in mag_arm], rest_chord,
             sum(r.data.bones[n].length for n in PARTS) * 1000, [round(x, 3) for x in (Wr @ v_perp)]), flush=True)
    # shipped round-1 baseline
    p = FIT[gun]['params']
    qb = swing_only(Matrix.Rotation(math.radians(p['a_z']), 4, 'Z').to_quaternion() @
                    Matrix.Rotation(math.radians(p['b_x']), 4, 'X').to_quaternion())
    apply_root(r, qb, p['c_02'], p['d_03'], keep)
    h, t, ch = chord_of(r, W)
    base = {'chord_mm': round(ch.length * 1000, 1), 'angle': round(math.degrees(math.acos(max(-1, min(1, ch.normalized().dot(mag_arm))))), 1),
            'rise_mm': round(ch.z * 1000, 1), 'along_mm': round(ch.dot(mag_arm) * 1000, 1),
            'twist': round(twist_deg(qb), 1), 'clear': measure(r, arms, tree_mag, tree_hand, W)}
    print('%s shipped(cur): chord %.1f mm angle %.1f rise %+.1f along %+.1f twist %.1f  %s'
          % (gun, base['chord_mm'], base['angle'], base['rise_mm'], base['along_mm'], base['twist'], base['clear']), flush=True)
    rows = []
    for tilt in TILTS:
        tgt = (Matrix.Rotation(math.radians(tilt), 3, tilt_axis) @ mag_arm).normalized()
        for c, d in FLEXIONS:
            # closed-form swing-only aim: the root's own +Y is taken exactly onto
            # the target, so the aim is deterministic and carries no twist.  The
            # chord then sits a few degrees off the root because the distal
            # segments keep their light flexion, which is the natural thumb shape.
            S3 = d_rest.rotation_difference(tgt).to_matrix()
            Bq = (M0.to_3x3().inverted() @ S3 @ M0.to_3x3()).to_quaternion()
            apply_root(r, Bq, c, d, keep)
            h, t, ch = chord_of(r, W)
            root_dir = (pose_matrices(r)['thumb_01_l'].to_3x3() @ Vector((0, 1, 0))).normalized()
            residual = math.degrees(math.acos(max(-1, min(1, root_dir.dot(tgt)))))
            pr = measure(r, arms, tree_mag, tree_hand, W)
            rows.append({'tilt': tilt, 'c_02': c, 'd_03': d, 'root_quat_wxyz': [round(x, 6) for x in Bq],
                         'root_twist_deg': round(twist_deg(Bq), 3), 'aim_residual_deg': round(residual, 2),
                         'chord_mm': round(ch.length * 1000, 1),
                         'straight_pct': round(ch.length / sum(r.data.bones[n].length for n in PARTS) * 100, 1),
                         'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, ch.normalized().dot(mag_arm))))), 1),
                         'rise_mm': round(ch.z * 1000, 1), 'along_mm': round(ch.dot(mag_arm) * 1000, 1),
                         'tip_arm_mm': [round(x * 1000, 1) for x in t], 'clear': pr})
            print('   %s tilt %5.1f flex %4.1f/%4.1f chord %5.1f mm (%4.1f%%) angle %5.1f res %5.2f rise %+7.1f along %+6.1f twist %5.2f mag[min %6.2f/%6.2f %6.2f/%6.2f] hand_min %s'
                  % (gun, tilt, c, d, rows[-1]['chord_mm'], rows[-1]['straight_pct'], rows[-1]['angle_to_mag_deg'],
                     rows[-1]['aim_residual_deg'], rows[-1]['rise_mm'], rows[-1]['along_mm'], rows[-1]['root_twist_deg'],
                     pr['thumb_02_l']['min'], pr['thumb_03_l']['min'], pr['thumb_02_l']['med'], pr['thumb_03_l']['med'],
                     [pr[k]['hand_min'] for k in PARTS]), flush=True)
    out[gun] = {'path': str(path), 'frame': FRAME, 'mag_proxy': [o.name for o in
                [x for x in sc.objects if x.type == 'MESH' and gun.upper() in x.name.upper() and 'MAG' in x.name.upper()]],
                'mag_axis_armature': [round(x, 4) for x in mag_arm],
                'rest_chord_mm': round(rest_chord, 1), 'shipped': base, 'candidates': rows}
(O / 'thumb_aim2.json').write_text(json.dumps(out, indent=1))
print('AIM2_OK', flush=True)
