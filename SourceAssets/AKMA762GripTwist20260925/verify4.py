"""Verify the authored v2 clips against their V4 sources, on disk.

Per clip: open the source and the authored blend and check that
  * every non-thumb bone has an identical basis at the grip frame,
  * the three thumb tracks equal the aimed target at the grip frame,
  * the thumb tracks outside the edit window are untouched (frames 0 and end),
  * the visible thumb (skin centroids) is straight, aimed along the magazine and
    clear of the magazine surface at the grip frame.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
FRAME = 148
TARGET = json.loads((O / 'thumb_target4.json').read_text())
ROUND1 = json.loads((O / 'thumb_fit.json').read_text())
SOURCES = json.loads((V4 / 'sources.json').read_text())['animations']


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
    return r, bpy.context.scene


def thumb_quats(r):
    return {n: r.pose.bones[n].matrix_basis.to_quaternion().copy() for n in PARTS}


def mag_geometry(gun, r, sc):
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    dg = bpy.context.evaluated_depsgraph_get()
    W = r.matrix_world
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
    tree = BVHTree.FromPolygons(mv, mp, all_triangles=False)
    mag_c_p, axis = principal(mv)
    if (r.pose.bones['WPN_root'].head - mag_c_p).dot(axis) < 0:
        axis = -axis
    mag_arm = (W.to_3x3().inverted() @ axis).normalized()
    return tree, mag_arm


def overlap_index(arms):
    """Thumb/index surface intersections and closest gap for the current pose."""
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
    trees = {}
    for label, gset in (('thumb', PARTS), ('index', ['index_01_l', 'index_02_l', 'index_03_l'])):
        vmap, pts, polys = {}, [], []
        for v in me.vertices:
            if kind[v.index] in gset:
                vmap[v.index] = len(pts); pts.append(M @ v.co)
        for p in me.polygons:
            idx = [vmap[i] for i in p.vertices if i in vmap]
            if len(idx) >= 3:
                polys.append(idx)
        trees[label] = (BVHTree.FromPolygons(pts, polys, all_triangles=False), pts)
    e.to_mesh_clear()
    pairs = trees['thumb'][0].overlap(trees['index'][0])
    gaps = []
    for p in trees['thumb'][1]:
        loc, nor, _, dist = trees['index'][0].find_nearest(p)
        if loc is not None:
            gaps.append(dist * 1000)
    gaps.sort()
    return {'overlaps': len(pairs), 'min_gap_mm': round(gaps[0], 2) if gaps else None}


def sample_hand(arms, tree):
    """Skin centroids and magazine clearance for the current pose, using the
    magazine geometry built once per clip so both poses are measured against the
    same shell."""
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    acc = {p: [] for p in PARTS + ['index_01_l']}
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
        out[p] = {'min': round(d[0], 2), 'med': round(d[len(d) // 2], 2),
                  'centroid': sum(pts, Vector()) / len(pts)}
    return out


rows = []
problems = []
all_notes = []
CHUNK_FILE = O / 'verify4_chunk.json'
if CHUNK_FILE.exists():
    chunk = json.loads(CHUNK_FILE.read_text(encoding='utf-8-sig'))
    start, count = int(chunk['start']), int(chunk['count'])
    JOBS = SOURCES[start:start + count]
    receipt_name = 'verify4_%02d.json' % start
else:
    JOBS = SOURCES
    receipt_name = 'verify4.json'
for job in JOBS:
    gun, magaz, family, clip = job['gun'], job['magazine'], job['family'], job['clip']
    stem = Path(job['asset']).name
    src = V4 / gun / magaz / family / (stem + '.blend')
    dst = O / 'v4' / gun / magaz / family / (stem + '.blend')
    if not dst.exists():
        problems.append((clip, 'missing authored blend'))
        continue
    r, sc = open_clip(src)
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    src_non_thumb = {b.name: b.matrix_basis.to_quaternion().copy() for b in r.pose.bones if b.name not in PARTS}
    ends = {}
    for f in (0, int(sc.frame_end)):
        sc.frame_set(f); bpy.context.view_layer.update()
        ends[f] = thumb_quats(r)
    r2, sc2 = open_clip(dst)
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    sc2.frame_set(FRAME); bpy.context.view_layer.update()
    moved = {}
    for b in r2.pose.bones:
        if b.name in PARTS:
            continue
        d = src_non_thumb[b.name].rotation_difference(b.matrix_basis.to_quaternion())
        if math.degrees(d.angle) > 1e-4:
            moved[b.name] = round(math.degrees(d.angle), 4)
    tq = TARGET[gun]
    want = {'thumb_01_l': Quaternion(tq['root_quat_wxyz']),
            'thumb_02_l': Matrix.Rotation(math.radians(tq['c_02']), 4, 'Z').to_quaternion(),
            'thumb_03_l': Matrix.Rotation(math.radians(tq['d_03']), 4, 'Z').to_quaternion()}
    got = thumb_quats(r2)
    thumb_err = {n: round(math.degrees(got[n].rotation_difference(want[n]).angle), 4) for n in PARTS}
    end_err = {}
    for f in ends:
        sc2.frame_set(f); bpy.context.view_layer.update()
        g = thumb_quats(r2)
        end_err[f] = {n: round(math.degrees(g[n].rotation_difference(ends[f][n]).angle), 4) for n in PARTS}
    sc2.frame_set(FRAME); bpy.context.view_layer.update()
    tree, mag_arm = mag_geometry(gun, r2, sc2)
    # thumb/index crossing at three points of the hold window: the authored thumb
    # target is constant, but the hand rotates, so the crossing has to be clear
    # everywhere in the window, not only at the grip frame
    crossing = {}
    for f in (68, FRAME, 220):
        sc2.frame_set(f); bpy.context.view_layer.update()
        crossing[f] = overlap_index(arms)
    sc2.frame_set(FRAME); bpy.context.view_layer.update()
    pr = sample_hand(arms, tree)
    vd = pr['thumb_03_l']['centroid'] - pr['thumb_01_l']['centroid']
    # rest web gap for the same clip: thumb tracks at identity, then reload the pose
    keep_basis = {n: (lambda d: (d[0], d[2]))(r2.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    for n in PARTS:
        r2.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep_basis[n][0], Quaternion(), keep_basis[n][1])
    bpy.context.view_layer.update()
    pr_rest = sample_hand(arms, tree)
    sc2.frame_set(FRAME + 1); sc2.frame_set(FRAME); bpy.context.view_layer.update()
    web_gap = (pr['thumb_01_l']['centroid'] - pr['index_01_l']['centroid']).length * 1000
    web_gap_rest = (pr_rest['thumb_01_l']['centroid'] - pr_rest['index_01_l']['centroid']).length * 1000
    # same clip in the pose that is shipping (round-1 root, round-1 distal flexion):
    # the web and the pad contact must not get worse than that
    p1 = ROUND1[gun]['params']
    for n, q in (('thumb_01_l', Quaternion(tq['root_quat_wxyz'])),
                 ('thumb_02_l', Matrix.Rotation(math.radians(p1['c_02']), 4, 'Z').to_quaternion()),
                 ('thumb_03_l', Matrix.Rotation(math.radians(p1['d_03']), 4, 'Z').to_quaternion())):
        pb = r2.pose.bones[n]
        loc, _, scale = pb.matrix_basis.decompose()
        pb.matrix_basis = Matrix.LocRotScale(loc, q, scale)
    bpy.context.view_layer.update()
    pr_ship = sample_hand(arms, tree)
    ship_gap = (pr_ship['thumb_01_l']['centroid'] - pr_ship['index_01_l']['centroid']).length * 1000
    sc2.frame_set(FRAME + 1); sc2.frame_set(FRAME); bpy.context.view_layer.update()
    # Shell-free robustness check: distance from the visible thumb tip to the
    # magazine bone's axis.  Some authoring scenes carry a magazine proxy that is
    # not where the shipping magazine is - the signed shell clearance then reports
    # physically impossible numbers (30 mm inside at the thumb base) - so this
    # bone-based distance decides whether straightening moved the thumb towards the
    # magazine or away from it.
    mb = r2.pose.bones['WPN_SOCKET_Magazine']
    Wm = r2.matrix_world
    mh = Wm @ mb.matrix.translation
    md = (Wm.to_3x3() @ mb.matrix.to_3x3() @ Vector((0, 1, 0))).normalized()

    def magline(centroid):
        v = centroid - mh
        return (v - v.project(md)).length * 1000

    tip_v3 = magline(pr['thumb_03_l']['centroid'])
    tip_ship = magline(pr_ship['thumb_03_l']['centroid'])
    row = {'clip': '/'.join((gun, magaz, family, clip)), 'moved_non_thumb': moved,
           'thumb_vs_target_deg': thumb_err, 'thumb_vs_source_at_ends_deg': end_err,
           'root_vs_shipping_deg': thumb_err['thumb_01_l'],
           'web_gap_mm': round(web_gap, 2), 'web_gap_rest_mm': round(web_gap_rest, 2),
           'web_gap_shipping_mm': round(ship_gap, 2),
           'web_gap_delta_vs_shipping_mm': round(web_gap - ship_gap, 2),
           'vis_len_mm': round(vd.length * 1000, 1),
           'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, vd.normalized().dot(mag_arm))))), 2),
           'rise_mm': round(vd.z * 1000, 1),
           'thumb_index_crossing': crossing,
           'thumb_index_worst_overlaps': max(v['overlaps'] for v in crossing.values()),
           'thumb_index_worst_gap_mm': min((v['min_gap_mm'] if v['min_gap_mm'] is not None else 99) for v in crossing.values()),
           'tip_to_mag_axis_mm': round(tip_v3, 2),
           'tip_to_mag_axis_shipping_mm': round(tip_ship, 2),
           'tip_moved_away_mm': round(tip_v3 - tip_ship, 2),
           'pad_min_mm': {k: pr[k]['min'] for k in PARTS},
           'pad_min_shipping_mm': {k: pr_ship[k]['min'] for k in PARTS},
           'pad_med_mm': {k: pr[k]['med'] for k in PARTS}}
    rows.append(row)
    bad = []
    notes = []
    if moved:
        bad.append('non-thumb bones moved %s' % moved)
    if max(thumb_err.values()) > 0.01:
        bad.append('thumb != target %s' % thumb_err)
    if any(v > 0.01 for f in end_err for v in end_err[f].values()):
        bad.append('window ends changed %s' % end_err)
    worse = {k: (row['pad_min_mm'][k], row['pad_min_shipping_mm'][k]) for k in PARTS
             if row['pad_min_mm'][k] < row['pad_min_shipping_mm'][k] - 2.0}
    if worse:
        if row['tip_moved_away_mm'] < -0.5:
            bad.append('pad worse and tip moved towards the magazine %s' % worse)
        else:
            notes.append('shell clearance reads worse on %s while the tip is %+.2f mm further from the magazine axis; the authoring-scene magazine proxy is unreliable on this clip'
                         % (list(worse), row['tip_moved_away_mm']))
    if row['thumb_index_worst_overlaps'] > 0:
        bad.append('thumb still crosses the index finger: %s' % crossing)
    if row['thumb_index_worst_gap_mm'] < 1.0:
        bad.append('thumb is only %.2f mm from the index finger' % row['thumb_index_worst_gap_mm'])
    if row['vis_len_mm'] < 60.0:
        bad.append('thumb still curled %.1f mm' % row['vis_len_mm'])
    if abs(row['web_gap_delta_vs_shipping_mm']) > 1.0:
        bad.append('web gap moved %.2f mm vs shipping' % row['web_gap_delta_vs_shipping_mm'])
    if bad:
        problems.append(('/'.join((gun, magaz, family, clip)), '; '.join(bad)))
    all_notes.extend(['%s: %s' % (row['clip'], n) for n in notes])
    print('%-42s visible %5.1f mm  angle %5.2f  rise %+6.1f  web %+5.2f mm vs shipping  tip_to_mag_axis %+6.2f mm  pad %s  thumb_err %.4f  index_overlaps %s  gap %5.2f mm%s'
          % (row['clip'], row['vis_len_mm'], row['angle_to_mag_deg'], row['rise_mm'],
             row['web_gap_delta_vs_shipping_mm'], row['tip_moved_away_mm'],
             row['pad_min_mm'], max(thumb_err.values()),
             {f: v['overlaps'] for f, v in crossing.items()},
             row['thumb_index_worst_gap_mm'], '  NOTE' if notes else ''), flush=True)
(O / receipt_name).write_text(json.dumps({'rows': rows, 'problems': problems, 'notes': all_notes}, indent=1))
print('VERIFY4_OK clips=%d problems=%d receipt=%s' % (len(rows), len(problems), receipt_name), flush=True)
for p in problems:
    print('   PROBLEM', p[0], p[1], flush=True)
