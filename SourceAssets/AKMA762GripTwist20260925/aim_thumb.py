"""Aim the AKM / A762 thumb: solve the swing-only root rotation that points the
extended thumb up along the magazine, instead of curling it into the web.

Round 1 fitted (root swing, distal flexion) jointly against pad clearance, which
landed on a heavily flexed thumb whose tip travels *into* the hand.  Here the
root is solved directly: minimal-arc swing from the thumb's rest direction to a
target derived from the magazine's own up axis (tilted by a small angle in the
magazine/palm plane), with the two distal segments left nearly straight.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
TILTS = (-20.0, -10.0, 0.0, 10.0, 20.0)
FLEXIONS = ((6.0, 5.0), (10.0, 8.0), (14.0, 10.0))
CASES = {
    'AKM': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend', 148),
    'A762': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend', 148),
}
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
    """Rotation of q about its own +Y (the bone length axis), in degrees."""
    q = q.copy(); q.normalize()
    a = Vector((0.0, 1.0, 0.0))
    p = a * Vector((q.x, q.y, q.z)).dot(a)
    if p.length < 1e-12:
        return 0.0
    return math.degrees(2.0 * math.atan2(p.length, q.w)) * (1.0 if p.dot(a) >= 0 else -1.0)


def setup(path, f):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action
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
    print('%s magazine meshes: %s (%d verts)' % (path.parent.name, [m.name for m in mags], len(mv)), flush=True)
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
        out[p] = {'min': round(d[0], 2), 'p05': round(d[len(d) // 20], 2), 'med': round(d[len(d) // 2], 2)}
    return out


def apply_root(r, q, c, d):
    for n, qq in (('thumb_01_l', q),
                  ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                  ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
        pb = r.pose.bones[n]
        loc, _, scale = pb.matrix_basis.decompose()
        pb.matrix_basis = Matrix.LocRotScale(loc, qq, scale)
    bpy.context.view_layer.update()


def aim_state(r):
    ident = {n: (lambda pb: (pb.matrix_basis.decompose()[0], pb.matrix_basis.decompose()[2]))(r.pose.bones[n])
             for n in PARTS}
    for n in PARTS:
        pb = r.pose.bones[n]
        pb.matrix_basis = Matrix.LocRotScale(ident[n][0], Quaternion(), ident[n][1])
    bpy.context.view_layer.update()
    return ident


out = {}
for gun, (path, f) in CASES.items():
    r, arms, sc, tree, mv = setup(path, f)
    W = r.matrix_world
    ident = aim_state(r)
    M0 = r.pose.bones['thumb_01_l'].matrix.copy()
    d_rest = (M0.to_3x3() @ Vector((0, 1, 0))).normalized()
    Wrot = W.to_3x3()
    mag_w = (Wrot @ r.pose.bones['WPN_SOCKET_Magazine'].matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
    if mag_w.z < 0:
        mag_w = -mag_w
    mag_arm = (Wrot.inverted() @ mag_w).normalized()
    mag_pts = [W.inverted() @ p for p in mv]
    c_mag = sum(mag_pts, Vector()) / len(mag_pts)
    c_hand = r.pose.bones['hand_l'].matrix.translation
    v = c_hand - c_mag
    v_perp = v - v.project(mag_arm)
    if v_perp.length < 1e-6:
        v_perp = Vector((1, 0, 0)) - Vector((1, 0, 0)).project(mag_arm)
    v_perp.normalize()
    tilt_axis = mag_arm.cross(v_perp).normalized()
    ln = [round(r.data.bones[n].length * 1000, 1) for n in PARTS]
    ang_rest = math.degrees(math.acos(max(-1, min(1, d_rest.dot(mag_arm)))))
    print('%s: thumb segs %s mm, rest-vs-mag-axis %.1f deg, mag axis world %s, palm-side %s'
          % (gun, ln, ang_rest, [round(x, 3) for x in mag_w], [round(x, 3) for x in (Wrot @ v_perp)]), flush=True)
    # shipped baseline
    p = FIT[gun]['params']
    qs = swing_only(Matrix.Rotation(math.radians(p['a_z']), 4, 'Z').to_quaternion() @
                    Matrix.Rotation(math.radians(p['b_x']), 4, 'X').to_quaternion())
    apply_root(r, qs, p['c_02'], p['d_03'])
    P = {b.name: b.matrix.copy() for b in r.pose.bones}
    head, tip = W @ P['thumb_01_l'].translation, W @ P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
    base_pr = measure(r, arms, tree)
    print('%s shipped(cur): tip_z %.1f mm, angle %.1f deg, root twist %.1f deg, clear %s'
          % (gun, tip.z * 1000, math.degrees(math.acos(max(-1, min(1, (tip - head).normalized().dot(mag_w))))),
             twist_deg(qs), base_pr), flush=True)
    shipped_tip_z = round(tip.z * 1000, 1)
    rows = []
    for tilt in TILTS:
        tgt = Matrix.Rotation(math.radians(tilt), 3, tilt_axis) @ mag_arm
        S3 = d_rest.rotation_difference(tgt).to_matrix()
        Bq = (M0.to_3x3().inverted() @ S3 @ M0.to_3x3()).to_quaternion()
        for c, d in FLEXIONS:
            apply_root(r, Bq, c, d)
            P = {b.name: b.matrix.copy() for b in r.pose.bones}
            head = W @ P['thumb_01_l'].translation
            tip = W @ P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
            dirw = (tip - head).normalized()
            pr = measure(r, arms, tree)
            rows.append({'tilt': tilt, 'c_02': c, 'd_03': d,
                         'root_quat_wxyz': [round(x, 6) for x in Bq],
                         'root_twist_deg': round(twist_deg(Bq), 3),
                         'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, dirw.dot(mag_w))))), 1),
                         'tip_z_mm': round(tip.z * 1000, 1),
                         'tip_mm': [round(x * 1000, 1) for x in tip],
                         'along_mag_mm': round((tip - head).dot(mag_w) * 1000, 1),
                         'clear': pr})
    good = [x for x in rows if x['clear']['thumb_03_l']['min'] > -1.5 and x['clear']['thumb_02_l']['min'] > -1.5]
    good.sort(key=lambda x: -x['tip_z_mm'])
    for x in rows:
        print('   %s tilt %5.1f flex %4.1f/%4.1f  angle %5.1f  tip_z %8.1f  along %6.1f  twist %5.2f  pad %5.1f/%5.1f med %5.1f/%5.1f'
              % (gun, x['tilt'], x['c_02'], x['d_03'], x['angle_to_mag_deg'], x['tip_z_mm'], x['along_mag_mm'],
                 x['root_twist_deg'], x['clear']['thumb_02_l']['min'], x['clear']['thumb_03_l']['min'],
                 x['clear']['thumb_02_l']['med'], x['clear']['thumb_03_l']['med']), flush=True)
    out[gun] = {'path': str(path), 'frame': f, 'mag_axis_world': [round(x, 4) for x in mag_w],
                'rest_angle_deg': round(ang_rest, 1), 'segs_mm': ln, 'shipped': base_pr,
                'shipped_tip_z_mm': shipped_tip_z, 'candidates': rows,
                'best': good[0] if good else None}
    # leave the rig in the chosen state for later rendering
    if good:
        b = good[0]
        apply_root(r, Quaternion(b['root_quat_wxyz']), b['c_02'], b['d_03'])
        print('%s CHOSEN tilt %s flex %s/%s -> tip_z %.1f tip %s clear %s'
              % (gun, b['tilt'], b['c_02'], b['d_03'], b['tip_z_mm'], b['tip_mm'], b['clear']), flush=True)
(O / 'thumb_aim.json').write_text(json.dumps(out, indent=1))
print('AIM_OK', flush=True)
