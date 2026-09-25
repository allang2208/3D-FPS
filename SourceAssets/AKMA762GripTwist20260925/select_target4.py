"""Build the final target: the natural extension (shipping root, distal 4/3) plus
one small extra swing that lifts the thumb above the index finger.

Direction: a swing about the hand's forward axis (hand -> middle knuckle), which
is the axis that raises the thumb over the curled fingers.  AKM needs 8 deg and
A762 16 deg before the thumb/index surfaces stop intersecting at all.

The candidate is checked across the whole hold window (the hand rotates during
the hold even though the thumb's own local pose is constant), so the lift has to
hold at every hold frame, not only at the grip frame used for aiming.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
INDEX = ['index_01_l', 'index_02_l', 'index_03_l']
FRAME = 148
HOLD_FRAMES = [44, 68, 92, 116, 148, 172, 196, 220, 237]
CASES = {
    'AKM': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend', -8.0),
    'A762': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend', -16.0),
}
TARGET = json.loads((O / 'thumb_target3.json').read_text())


def open_clip(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    act = r.animation_data.action
    r.animation_data.action_slot = act.slots[0]
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    return r, sc


def set_thumb(r, root, c, d, keep):
    for n, q in (('thumb_01_l', root),
                 ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                 ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep[n][0], q, keep[n][1])
    bpy.context.view_layer.update()


def set_basis(r, q1, q2, q3, keep):
    for n, q in (('thumb_01_l', q1), ('thumb_02_l', q2), ('thumb_03_l', q3)):
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep[n][0], q, keep[n][1])
    bpy.context.view_layer.update()


def clouds(arms, W):
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    names = [g.name for g in arms.vertex_groups]
    kind = {}
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = names[g.group], g.weight
        kind[v.index] = best
    out = {}
    for label, gset in (('thumb', PARTS), ('index', INDEX)):
        vmap, pts, polys = {}, [], []
        for v in me.vertices:
            if kind[v.index] in gset:
                vmap[v.index] = len(pts); pts.append(M @ v.co)
        for p in me.polygons:
            idx = [vmap[i] for i in p.vertices if i in vmap]
            if len(idx) >= 3:
                polys.append(idx)
        out[label] = (pts, polys)
    cent = {g: [] for g in PARTS + INDEX}
    for v in me.vertices:
        b = kind[v.index]
        if b in cent:
            cent[b].append(M @ v.co)
    e.to_mesh_clear()
    out['centroid'] = {k: sum(v, Vector()) / len(v) for k, v in cent.items() if v}
    return out


def overlap_and_gap(arm_data):
    tv, tp = arm_data['thumb']
    iv, ip = arm_data['index']
    tt = BVHTree.FromPolygons(tv, tp, all_triangles=False)
    it = BVHTree.FromPolygons(iv, ip, all_triangles=False)
    pairs = tt.overlap(it)
    gaps = []
    for p in tv:
        loc, nor, _, dist = it.find_nearest(p)
        if loc is not None:
            gaps.append(dist * 1000)
    gaps.sort()
    return len(pairs), (round(gaps[0], 2) if gaps else None)


out = {}
for gun, (path, angle) in CASES.items():
    r, sc = open_clip(path)
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    W = r.matrix_world
    keep = {n: (lambda dd: (dd[0], dd[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    q3 = Quaternion(TARGET[gun]['root_quat_wxyz'])
    C, D = TARGET[gun]['c_02'], TARGET[gun]['d_03']
    set_thumb(r, q3, C, D, keep)
    P = {b.name: b.matrix.copy() for b in r.pose.bones}
    centre = W @ P['hand_l'].translation
    fwd = (W @ P['middle_01_l'].translation - centre).normalized()
    M0 = P['thumb_01_l'].to_3x3()
    d0 = clouds(arms, W)
    vis = (d0['centroid']['thumb_03_l'] - d0['centroid']['thumb_01_l']).normalized()
    perp = (fwd - vis * fwd.dot(vis)).normalized()
    R = Matrix.Rotation(math.radians(angle), 3, perp)
    q4 = (M0.inverted() @ R @ M0 @ q3.to_matrix()).to_quaternion()
    web0 = (d0['centroid']['thumb_01_l'] - d0['centroid']['index_01_l']).length * 1000
    print('%s: extra swing %.1f deg about fwd (perpendicular to the visible thumb), root %s'
          % (gun, angle, [round(x, 6) for x in q4]), flush=True)
    rows = []
    for f in HOLD_FRAMES:
        sc.frame_set(f); bpy.context.view_layer.update()
        keep_f = {n: (lambda dd: (dd[0], dd[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
        base = {n: r.pose.bones[n].matrix_basis.to_quaternion().copy() for n in PARTS}
        # (shipping pose of this frame is read straight from the clip keys)
        # the V4 source clip's own thumb at this frame (the round-1 shipping pose is\n        # a constant target inside the hold, so its web gap is measured separately)
        set_basis(r, base['thumb_01_l'], base['thumb_02_l'], base['thumb_03_l'], keep_f)
        ship = clouds(arms, W)
        ship_web = (ship['centroid']['thumb_01_l'] - ship['centroid']['index_01_l']).length * 1000
        ship_ov, ship_gap = overlap_and_gap(ship)
        set_thumb(r, q4, C, D, keep_f)
        d = clouds(arms, W)
        ov, gap = overlap_and_gap(d)
        web = (d['centroid']['thumb_01_l'] - d['centroid']['index_01_l']).length * 1000
        visv = d['centroid']['thumb_03_l'] - d['centroid']['thumb_01_l']
        rows.append({'frame': f, 'overlaps': ov, 'min_gap_mm': gap, 'shipping_overlaps': ship_ov,
                     'shipping_min_gap_mm': ship_gap, 'web_gap_vs_v4_source_mm': round(web - ship_web, 2),
                     'visible_len_mm': round(visv.length * 1000, 1)})
        print('   frame %3d  overlaps %3d (shipping %3d)  min_gap %6.2f (shipping %6.2f)  web %+5.2f mm  visible %5.1f mm'
              % (f, ov, ship_ov, gap if gap is not None else -1, ship_gap if ship_gap is not None else -1,
                 rows[-1]['web_gap_vs_v4_source_mm'], rows[-1]['visible_len_mm']), flush=True)
    bad = [x for x in rows if x['overlaps'] > 0]
    out[gun] = {'root_quat_wxyz': [round(x, 6) for x in q4], 'c_02': C, 'd_03': D,
                'extra_swing_axis': 'fwd', 'extra_swing_deg': angle,
                'extra_swing_axis_armature': [round(x, 4) for x in perp],
                'v3_root_wxyz': [round(x, 6) for x in q3],
                'frames': rows, 'clean_frames': len(rows) - len(bad),
                'worst_overlaps': max(x['overlaps'] for x in rows),
                'worst_web_delta_vs_v4_source_mm': max(abs(x['web_gap_vs_v4_source_mm']) for x in rows),
                'shipping_worst_overlaps': max(x['shipping_overlaps'] for x in rows)}
    print('%s -> frames clean %d/%d, worst overlaps %d (shipping %d), worst web delta vs V4 source %.2f mm'
          % (gun, out[gun]['clean_frames'], len(rows), out[gun]['worst_overlaps'],
             out[gun]['shipping_worst_overlaps'], out[gun]['worst_web_delta_vs_v4_source_mm']), flush=True)
(O / 'thumb_target4.json').write_text(json.dumps(out, indent=1))
print('SELECT_V4_OK', flush=True)
