"""Check the aimed thumb target against every one of the 30 clips.

For each clip: build that clip's own posed magazine proxy, apply the chosen
per-gun root swing + flexion, and report the thumb chord, the angle to that
clip's magazine axis, the tip travel along the axis, and the pad clearance to
that clip's magazine.  Families insert the magazine at different angles, so this
tells us whether one target per gun is enough or a per-family aim is needed.
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


def mag_points(sc, gun, D, dg):
    """Posed magazine geometry: the gun's own magazine proxy when it is a
    magazine-sized object, otherwise the A762 magazine library part."""
    cands = [o for o in sc.objects if o.type == 'MESH' and gun.upper() in o.name.upper() and 'MAG' in o.name.upper()]
    mv, mp, used = [], [], []
    for o in cands:
        if any(m.type == 'ARMATURE' for m in o.modifiers):
            e = o.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
            pts = [M @ v.co for v in me.vertices]
            polys = [list(p.vertices) for p in me.polygons]
            e.to_mesh_clear()
        else:
            pts = [D @ (o.matrix_world @ v.co) for v in o.data.vertices]
            polys = [list(p.vertices) for p in o.data.polygons]
        if not pts:
            continue
        ext = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3)) * 1000
        if ext > 400:
            continue
        off = len(mv)
        mv.extend(pts)
        mp.extend([[off + i for i in p] for p in polys])
        used.append((o.name, round(ext, 1)))
    if mv:
        return mv, mp, used, False
    with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
    for o in dst.objects:
        if o is None:
            continue
        sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
        off = len(mv)
        mv.extend(D @ (o.matrix_world @ v.co) for v in o.data.vertices)
        mp.extend([[off + i for i in p.vertices] for p in o.data.polygons])
        used.append((o.name, None))
    return mv, mp, used, True


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
            if loc is not None:
                d.append(-dist * 1000 if (q - loc).dot(nor) < 0 else dist * 1000)
        d.sort()
        out[p] = {'min': round(d[0], 2), 'p05': round(d[len(d) // 20], 2), 'med': round(d[len(d) // 2], 2),
                  'centroid': sum(pts, Vector()) / len(pts)}
    return out


jobs = json.loads((V4 / 'sources.json').read_text())['animations']
rows = []
axes = {}
for job in jobs:
    gun, magaz, family, clip = job['gun'], job['magazine'], job['family'], job['clip']
    stem = Path(job['asset']).name
    src = V4 / gun / magaz / family / (stem + '.blend')
    if not src.exists():
        print('MISSING', src, flush=True)
        continue
    bpy.ops.wm.open_mainfile(filepath=str(src), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    act = r.animation_data.action
    r.animation_data.action_slot = act.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    W = r.matrix_world; dg = bpy.context.evaluated_depsgraph_get()
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    D = W @ pose['WPN_SOCKET_Magazine'] @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ W.inverted()
    mv, mp, used, lib = mag_points(sc, gun, D, dg)
    tree = BVHTree.FromPolygons(mv, mp, all_triangles=False)
    mag_c_p, axis = principal(mv)
    anchor = r.pose.bones['WPN_root'].head if 'WPN_root' in r.pose.bones else pose['hand_r'].translation
    if (anchor - mag_c_p).dot(axis) < 0:
        axis = -axis
    Wr = W.to_3x3()
    mag_arm = (Wr.inverted() @ axis).normalized()
    # rest visible thumb length for this clip (thumb tracks at identity)
    rest_basis = {}
    for n in PARTS:
        loc, _, scale = r.pose.bones[n].matrix_basis.decompose()
        rest_basis[n] = (loc, scale)
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(loc, Quaternion(), scale)
    bpy.context.view_layer.update()
    pr_rest = measure(r, arms, tree)
    rest_vd = pr_rest['thumb_03_l']['centroid'] - pr_rest['thumb_01_l']['centroid']
    tg = TARGET[gun]
    for n, q in (('thumb_01_l', Quaternion(tg['root_quat_wxyz'])),
                 ('thumb_02_l', Matrix.Rotation(math.radians(tg['c_02']), 4, 'Z').to_quaternion()),
                 ('thumb_03_l', Matrix.Rotation(math.radians(tg['d_03']), 4, 'Z').to_quaternion())):
        loc, scale = rest_basis[n]
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(loc, q, scale)
    bpy.context.view_layer.update()
    pr = measure(r, arms, tree)
    vd = pr['thumb_03_l']['centroid'] - pr['thumb_01_l']['centroid']
    key = '%s/%s' % (gun, magaz)
    base_ang = None
    if family == 'base':
        axes[key] = mag_arm.copy()
    elif key in axes:
        base_ang = round(math.degrees(math.acos(max(-1, min(1, mag_arm.dot(axes[key]))))), 1)
    row = {'clip': '/'.join((gun, magaz, family, clip)), 'family': family, 'gun': gun,
           'proxy': used[:2], 'library_fallback': lib,
           'vis_len_mm': round(vd.length * 1000, 1),
           'vis_vs_rest_pct': round(vd.length / rest_vd.length * 100, 1),
           'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, vd.normalized().dot(mag_arm))))), 1),
           'rise_mm': round(vd.z * 1000, 1), 'along_mag_mm': round(vd.dot(mag_arm) * 1000, 1),
           'axis_vs_base_deg': base_ang, 'clear': {k: {kk: vv for kk, vv in v.items() if kk != 'centroid'}
                                                   for k, v in pr.items()}}
    rows.append(row)
    print('%-42s visible %5.1f mm (%5.1f%%) angle %5.1f rise %+6.1f along %+6.1f axisVsBase %5s  pad min %6.2f/%6.2f med %5.1f/%5.1f  proxy %s'
          % (row['clip'], row['vis_len_mm'], row['vis_vs_rest_pct'], row['angle_to_mag_deg'], row['rise_mm'],
             row['along_mag_mm'], base_ang, pr['thumb_02_l']['min'], pr['thumb_03_l']['min'],
             pr['thumb_02_l']['med'], pr['thumb_03_l']['med'], used[0][0] if used else None), flush=True)
(O / 'family_check.json').write_text(json.dumps(rows, indent=1))
bad = [x for x in rows if x['clear']['thumb_03_l']['min'] < -2.0 or x['clear']['thumb_02_l']['min'] < -2.0]
print('FAMILY_CHECK_OK clips=%d penetrating=%d' % (len(rows), len(bad)), flush=True)
for x in bad:
    print('   PENETRATION', x['clip'], x['clear']['thumb_02_l']['min'], x['clear']['thumb_03_l']['min'], flush=True)
