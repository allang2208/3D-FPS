"""Lift the AKM / A762 thumb clear of the index finger.

With the root untouched and the two distal segments straight (the accepted
natural extension), the thumb shaft crosses the index finger.  This script
measures exactly that crossing - triangle overlap between the skinned thumb and
index surfaces, plus how far apart the two surfaces are - and searches for the
smallest extra root swing that clears it while keeping the thumb extended and the
web where it is.

The extra rotation is applied about an axis perpendicular to the visible thumb
direction (a pure swing about the thumb, so the accepted roll is preserved), and
every candidate is scored on

  overlap        number of intersecting thumb/index face pairs, and which bone
                 groups they belong to
  gap            closest distance between the thumb and index surfaces
  side           where the thumb sits relative to the index along the hand
                 normal (positive = further towards the back of the hand, i.e.
                 "above" the index)
  visible/web    visible thumb length and direction, and the web gap
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
INDEX = ['index_01_l', 'index_02_l', 'index_03_l']
WEBB = ['thumb_01_l', 'index_01_l']
FRAME = 148
CASES = {
    'AKM': S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
    'A762': S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
}
TARGET = json.loads((O / 'thumb_target3.json').read_text())
ANGLE_STEPS = [0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 26.0, 32.0]


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


def cloud(arms, groups_wanted):
    """Pose-space vertices and faces for the wanted vertex groups."""
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
    verts, polys, vmap = [], [], {}
    for v in me.vertices:
        if kind[v.index] in groups_wanted:
            vmap[v.index] = len(verts); verts.append(M @ v.co)
    for p in me.polygons:
        idx = [vmap[i] for i in p.vertices if i in vmap]
        if len(idx) >= 3:
            polys.append(idx)
    e.to_mesh_clear()
    return verts, polys, kind


def hand_frame(r, W):
    P = {b.name: b.matrix.copy() for b in r.pose.bones}
    centre = W @ P['hand_l'].translation
    fwd = (W @ P['middle_01_l'].translation - centre).normalized()
    across = (W @ P['index_01_l'].translation - W @ P['pinky_01_l'].translation).normalized()
    normal = across.cross(fwd).normalized()
    return fwd, across, normal


rows = []
best_all = {}
for gun, path in CASES.items():
    r, sc = open_clip(path)
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    W = r.matrix_world
    keep = {n: (lambda dd: (dd[0], dd[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    q3 = Quaternion(TARGET[gun]['root_quat_wxyz'])
    C, D = TARGET[gun]['c_02'], TARGET[gun]['d_03']
    fwd, across, normal = hand_frame(r, W)
    set_thumb(r, q3, C, D, keep)
    tv, tp, tkind = cloud(arms, PARTS)
    iv, ip, ikind = cloud(arms, INDEX)
    # regroup thumb vertices by group name
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    names = [g.name for g in arms.vertex_groups]
    pos_of = {}
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = names[g.group], g.weight
        pos_of[v.index] = (best, M @ v.co)
    cent = {g: [] for g in PARTS + INDEX}
    for idx, (g, p) in pos_of.items():
        if g in cent:
            cent[g].append(p)
    e.to_mesh_clear()
    vis = (sum(cent['thumb_03_l'], Vector()) / len(cent['thumb_03_l'])) - \
          (sum(cent['thumb_01_l'], Vector()) / len(cent['thumb_01_l']))
    web_gap0 = ((sum(cent['thumb_01_l'], Vector()) / len(cent['thumb_01_l'])) -
                (sum(cent['index_01_l'], Vector()) / len(cent['index_01_l']))).length * 1000
    M0 = {b.name: b.matrix.copy() for b in r.pose.bones}['thumb_01_l'].to_3x3()
    print('%s baseline v3: visible %.1f mm, %d thumb verts, %d index verts'
          % (gun, vis.length * 1000, len(tv), len(iv)), flush=True)
    results = []
    axes = [('normal', normal), ('-normal', -normal), ('across', across), ('-across', -across),
            ('fwd', fwd), ('-fwd', -fwd)]
    for aname, ax in axes:
        perp = ax - vis.normalized() * ax.dot(vis.normalized())
        if perp.length < 1e-6:
            continue
        perp.normalize()
        for ang in ANGLE_STEPS:
            R = Matrix.Rotation(math.radians(ang), 3, perp)
            Mcur = {b.name: b.matrix.copy() for b in r.pose.bones}['thumb_01_l'].to_3x3()
            q = (M0.inverted() @ R @ M0 @ q3.to_matrix()).to_quaternion()
            set_thumb(r, q, C, D, keep)
            tv2, tp2, _ = cloud(arms, PARTS)
            iv2, ip2, _ = cloud(arms, INDEX)
            overlap = BVHTree.FromPolygons(tv2, tp2, all_triangles=False).overlap(
                BVHTree.FromPolygons(iv2, ip2, all_triangles=False))
            tree_i = BVHTree.FromPolygons(iv2, ip2, all_triangles=False)
            gaps = []
            for p in tv2:
                loc, nor, _, dist = tree_i.find_nearest(p)
                if loc is not None:
                    gaps.append(dist * 1000)
            gaps.sort()
            dg = bpy.context.evaluated_depsgraph_get()
            e = arms.evaluated_get(dg); me = e.to_mesh(); Mx = e.matrix_world
            names = [g.name for g in arms.vertex_groups]
            cc = {g: [] for g in PARTS + INDEX}
            for v in me.vertices:
                best, w = None, 0.0
                for g in v.groups:
                    if g.weight > w:
                        best, w = names[g.group], g.weight
                if best in cc:
                    cc[best].append(Mx @ v.co)
            e.to_mesh_clear()
            cth = sum(cc['thumb_02_l'] + cc['thumb_03_l'], Vector()) / max(1, len(cc['thumb_02_l'] + cc['thumb_03_l']))
            cix = sum(cc['index_01_l'] + cc['index_02_l'] + cc['index_03_l'], Vector()) / \
                max(1, len(cc['index_01_l'] + cc['index_02_l'] + cc['index_03_l']))
            side = (cth - cix).dot(normal) * 1000
            web_gap = ((sum(cc['thumb_01_l'], Vector()) / len(cc['thumb_01_l'])) -
                       (sum(cc['index_01_l'], Vector()) / len(cc['index_01_l']))).length * 1000
            vis2 = (sum(cc['thumb_03_l'], Vector()) / len(cc['thumb_03_l'])) - \
                   (sum(cc['thumb_01_l'], Vector()) / len(cc['thumb_01_l']))
            results.append({'axis': aname, 'angle_deg': ang, 'overlaps': len(overlap),
                            'min_gap_mm': round(gaps[0], 2) if gaps else None,
                            'p05_gap_mm': round(gaps[len(gaps) // 20], 2) if gaps else None,
                            'thumb_vs_index_side_mm': round(side, 2),
                            'web_gap_mm': round(web_gap, 2),
                            'web_gap_vs_v3_mm': round(web_gap - web_gap0, 2),
                            'visible_len_mm': round(vis2.length * 1000, 1),
                            'root_quat_wxyz': [round(x, 6) for x in q],
                            'root_axis_armature': [round(x, 4) for x in perp]})
            print('   %-8s %5.1f deg  overlaps %3d  min_gap %6.2f  p05 %6.2f  side %+7.2f  web %+5.2f  visible %5.1f mm'
                  % (aname, ang, results[-1]['overlaps'], results[-1]['min_gap_mm'] or -1,
                     results[-1]['p05_gap_mm'] or -1, side, results[-1]['web_gap_vs_v3_mm'],
                     results[-1]['visible_len_mm']), flush=True)
    clean = [x for x in results if x['overlaps'] == 0 and (x['min_gap_mm'] or 0) >= 1.0]
    clean.sort(key=lambda x: x['angle_deg'])
    best = clean[0] if clean else None
    best_all[gun] = {'baseline_visible_mm': round(vis.length * 1000, 1),
                     'baseline_web_gap_mm': round(web_gap0, 2),
                     'v3_root_wxyz': [round(x, 6) for x in q3],
                     'c_02': C, 'd_03': D, 'best': best,
                     'all': results}
    if best:
        print('%s CHOSEN %s at %.1f deg: overlaps %d, min_gap %.2f mm, side %+.2f mm, web %+.2f mm, visible %.1f mm'
              % (gun, best['axis'], best['angle_deg'], best['overlaps'], best['min_gap_mm'],
                 best['thumb_vs_index_side_mm'], best['web_gap_vs_v3_mm'], best['visible_len_mm']), flush=True)
    else:
        print('%s: no clean candidate' % gun, flush=True)
(O / 'thumb_index.json').write_text(json.dumps(best_all, indent=1))
print('THUMB_INDEX_OK', flush=True)
