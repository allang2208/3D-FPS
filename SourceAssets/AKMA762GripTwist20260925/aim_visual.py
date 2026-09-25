"""Aim the visible thumb.

The left-thumb bones in this rig are laid out with their own +Y pointing away
from the visible phalanx direction (consecutive thumb bones are offset ~50 mm
along the chain while each bone's axis points back down the hand), so the bone
head->tail chord is not what the player sees.  Everything here is therefore
measured from the skinned mesh: the thumb direction is the vector from the
centroid of the ``thumb_01_l`` skin to the centroid of the ``thumb_03_l`` skin,
and the aim solves the swing-only root rotation that puts that visible direction
onto the magazine's own long axis (tilted in the magazine/palm plane).  The two
distal segments keep a light flexion, the palm and the four fingers are frozen.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
HAND_BONES = [b + '_l' for b in ('index_01', 'index_02', 'index_03', 'middle_01', 'middle_02',
                                 'middle_03', 'ring_01', 'ring_02', 'ring_03', 'pinky_01',
                                 'pinky_02', 'pinky_03', 'hand')]
FRAME = 148
TILTS = [-30.0, -25.0, -20.0, -15.0, -10.0, -5.0, 0.0, 5.0, 10.0, 15.0, 20.0, 30.0]
FLEXIONS = [(4.0, 3.0), (8.0, 6.0), (12.0, 9.0), (0.0, 0.0)]
CASES = {
    'AKM': S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
    'A762': S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
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
    D = W @ pose['WPN_SOCKET_Magazine'] @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ W.inverted()
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
    anchor = r.pose.bones['WPN_root'].head if 'WPN_root' in r.pose.bones else pose['hand_r'].translation
    if (anchor - mag_c_p).dot(axis) < 0:
        axis = -axis
    Wr = W.to_3x3()
    mag_c = Wr.inverted() @ mag_c_p
    mag_arm = (Wr.inverted() @ axis).normalized()
    v = r.pose.bones['hand_l'].matrix.translation - mag_c
    v_perp = v - v.project(mag_arm)
    v_perp.normalize()
    tilt_axis = mag_arm.cross(v_perp).normalized()
    return r, arms, sc, W, BVHTree.FromPolygons(mv, mp, all_triangles=False), mag_arm, tilt_axis, v_perp


def measure(r, arms, tree):
    """Per-segment clearance to the magazine and to the rest of the left hand,
    plus the skin centroids used to define the visible thumb direction."""
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    acc = {p: [] for p in PARTS}
    hand = []
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if best in acc:
            acc[best].append(M @ v.co)
        elif best in HAND_BONES:
            hand.append(M @ v.co)
    e.to_mesh_clear()
    out = {}
    for p, pts in acc.items():
        d = []
        for q in pts:
            loc, nor, _, dist = tree.find_nearest(q)
            if loc is not None:
                d.append(-dist * 1000 if (q - loc).dot(nor) < 0 else dist * 1000)
        d.sort()
        c = sum(pts, Vector()) / len(pts)
        out[p] = {'min': round(d[0], 2), 'med': round(d[len(d) // 2], 2),
                  'centroid': c}
    return out


def apply_root(r, q, c, d, keep):
    for n, qq in (('thumb_01_l', q),
                  ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                  ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
        pb = r.pose.bones[n]
        loc, scale = keep.get(n, (Vector(), Vector((1, 1, 1))))
        pb.matrix_basis = Matrix.LocRotScale(loc, qq, scale)
    bpy.context.view_layer.update()


def vis_dir(pr, W):
    a = W @ pr['thumb_01_l']['centroid']
    b = W @ pr['thumb_03_l']['centroid']
    return b - a


out = {}
for gun, path in CASES.items():
    r, arms, sc, W, tree, mag_arm, tilt_axis, v_perp = setup(gun, path)
    keep = {n: (lambda d: (d[0], d[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    for n in PARTS:
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep[n][0], Quaternion(), keep[n][1])
    bpy.context.view_layer.update()
    P = {b.name: b.matrix.copy() for b in r.pose.bones}
    rest = measure(r, arms, tree)
    restdir = vis_dir(rest, W).normalized()
    print('%s: rest visible thumb dir %s  length %.1f mm  vs mag axis %.1f deg'
          % (gun, [round(x, 3) for x in restdir], vis_dir(rest, W).length * 1000,
             math.degrees(math.acos(max(-1, min(1, restdir.dot(mag_arm)))))), flush=True)
    rows = []
    for tilt in TILTS:
        tgt = (Matrix.Rotation(math.radians(tilt), 3, tilt_axis) @ mag_arm).normalized()
        for c, d in FLEXIONS:
            Bq = Quaternion()
            prev = None
            for _ in range(24):
                apply_root(r, Bq, c, d, keep)
                pr = measure(r, arms, tree)
                cur = vis_dir(pr, W).normalized()
                R = cur.rotation_difference(tgt).to_matrix()
                if R.to_quaternion().angle < 1e-4:
                    break
                if prev is not None and R.to_quaternion().angle > prev - 1e-9:
                    break
                prev = R.to_quaternion().angle
                M = {b.name: b.matrix.copy() for b in r.pose.bones}['thumb_01_l'].to_3x3()
                Bq = swing_only((M.inverted() @ R @ M @ Bq.to_matrix()).to_quaternion())
            apply_root(r, Bq, c, d, keep)
            pr = measure(r, arms, tree)
            vd = vis_dir(pr, W)
            rows.append({'tilt': tilt, 'c_02': c, 'd_03': d,
                         'root_quat_wxyz': [round(x, 6) for x in Bq],
                         'root_twist_deg': round(twist_deg(Bq), 3),
                         'residual_deg': round(math.degrees(math.acos(max(-1, min(1, vd.normalized().dot(tgt))))), 2),
                         'vis_len_mm': round(vd.length * 1000, 1),
                         'vis_vs_rest_pct': round(vd.length / vis_dir(rest, W).length * 100, 1),
                         'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, vd.normalized().dot(mag_arm))))), 1),
                         'rise_mm': round(vd.z * 1000, 1),
                         'along_mag_mm': round(vd.dot(mag_arm) * 1000, 1),
                         'clear': {k: {'min': v['min'], 'med': v['med']} for k, v in pr.items()}})
            print('   %s tilt %5.1f flex %4.1f/%4.1f  len %5.1f mm (%5.1f%% of rest)  angle %5.1f res %5.2f  rise %+7.1f along %+6.1f twist %5.2f  mag min %6.2f/%6.2f med %6.2f/%6.2f'
                  % (gun, tilt, c, d, rows[-1]['vis_len_mm'], rows[-1]['vis_vs_rest_pct'],
                     rows[-1]['angle_to_mag_deg'], rows[-1]['residual_deg'], rows[-1]['rise_mm'],
                     rows[-1]['along_mag_mm'], rows[-1]['root_twist_deg'],
                     pr['thumb_02_l']['min'], pr['thumb_03_l']['min'],
                     pr['thumb_02_l']['med'], pr['thumb_03_l']['med']), flush=True)
    out[gun] = {'path': str(path), 'frame': FRAME, 'mag_axis_armature': [round(x, 4) for x in mag_arm],
                'rest_vis_len_mm': round(vis_dir(rest, W).length * 1000, 1),
                'rest_vis_dir': [round(x, 3) for x in restdir],
                'rest_angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, restdir.dot(mag_arm))))), 1),
                'candidates': rows}
(O / 'thumb_aim_visual.json').write_text(json.dumps(out, indent=1))
print('AIM_VISUAL_OK', flush=True)
