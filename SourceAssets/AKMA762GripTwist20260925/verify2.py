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
TARGET = json.loads((O / 'thumb_target2.json').read_text())
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


def posed_hand(gun, r, sc):
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
        out[p] = {'min': round(d[0], 2), 'med': round(d[len(d) // 2], 2),
                  'centroid': sum(pts, Vector()) / len(pts)}
    return out, mag_arm


rows = []
problems = []
for job in SOURCES:
    gun, magaz, family, clip = job['gun'], job['magazine'], job['family'], job['clip']
    stem = Path(job['asset']).name
    src = V4 / gun / magaz / family / (stem + '.blend')
    dst = O / 'v2' / gun / magaz / family / (stem + '.blend')
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
    pr, mag_arm = posed_hand(gun, r2, sc2)
    vd = pr['thumb_03_l']['centroid'] - pr['thumb_01_l']['centroid']
    row = {'clip': '/'.join((gun, magaz, family, clip)), 'moved_non_thumb': moved,
           'thumb_vs_target_deg': thumb_err, 'thumb_vs_source_at_ends_deg': end_err,
           'vis_len_mm': round(vd.length * 1000, 1),
           'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, vd.normalized().dot(mag_arm))))), 2),
           'rise_mm': round(vd.z * 1000, 1),
           'pad_min_mm': {k: pr[k]['min'] for k in PARTS},
           'pad_med_mm': {k: pr[k]['med'] for k in PARTS}}
    rows.append(row)
    bad = []
    if moved:
        bad.append('non-thumb bones moved %s' % moved)
    if max(thumb_err.values()) > 0.01:
        bad.append('thumb != target %s' % thumb_err)
    if any(v > 0.01 for f in end_err for v in end_err[f].values()):
        bad.append('window ends changed %s' % end_err)
    if pr['thumb_03_l']['min'] < -2.0 or pr['thumb_02_l']['min'] < -2.0:
        bad.append('magazine penetration %s' % row['pad_min_mm'])
    if row['vis_len_mm'] < 60.0:
        bad.append('thumb still curled %.1f mm' % row['vis_len_mm'])
    if bad:
        problems.append(('/'.join((gun, magaz, family, clip)), '; '.join(bad)))
    print('%-42s visible %5.1f mm  angle %5.2f  rise %+6.1f  pad %s  moved_non_thumb %d  thumb_err %.4f deg'
          % (row['clip'], row['vis_len_mm'], row['angle_to_mag_deg'], row['rise_mm'],
             row['pad_min_mm'], len(moved), max(thumb_err.values())), flush=True)
(O / 'verify2.json').write_text(json.dumps({'rows': rows, 'problems': problems}, indent=1))
print('VERIFY2_OK clips=%d problems=%d' % (len(rows), len(problems)), flush=True)
for p in problems:
    print('   PROBLEM', p[0], p[1], flush=True)
