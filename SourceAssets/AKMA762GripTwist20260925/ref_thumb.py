"""Measure the accepted SVD thumb-up grip and the shipped AKM / A762 thumbs with
the same quantities, so the AKM / A762 target can be taken from the reference
instead of guessed.

Per case: thumb segment orientations vs rest (swing / twist about the bone's own
+Y), the thumb direction in world, the magazine's own long axis (principal axis
of the posed magazine mesh, signed toward the feed end / weapon), the angle
between them, and how far the tip rises and travels along that axis.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
CASES = [
    ('SVD', S / 'SVDThumbUp20260923/SVD_base_Editable.blend', 'A_SVD_reload', 148),
    ('M4', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', None, 76),
    ('AKM', S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend', None, 148),
    ('A762', S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend', None, 148),
]


def swing_twist(q):
    q = q.copy(); q.normalize()
    a = Vector((0.0, 1.0, 0.0))
    p = a * Vector((q.x, q.y, q.z)).dot(a)
    if p.length < 1e-12:
        return 0.0, 0.0
    tw = math.degrees(2.0 * math.atan2(p.length, q.w)) * (1.0 if p.dot(a) >= 0 else -1.0)
    sw = q @ Quaternion(a, math.radians(tw)).inverted()
    sw.normalize()
    ang = math.degrees(2.0 * math.acos(max(-1.0, min(1.0, abs(sw.w)))))
    return ang, tw


def principal(points):
    c = sum(points, Vector()) / len(points)
    xx = xy = xz = yy = yz = zz = 0.0
    for p in points:
        d = p - c
        xx += d.x * d.x; xy += d.x * d.y; xz += d.x * d.z
        yy += d.y * d.y; yz += d.y * d.z; zz += d.z * d.z
    M = Matrix(((xx, xy, xz), (xy, yy, yz), (xz, yz, zz)))
    best, bl = None, -1.0
    for i in range(3):
        v = Vector((M[0][i], M[1][i], M[2][i]))
        if v.length > bl:
            best, bl = v.normalized(), v.length
    return c, best, bl


rows = {}
for tag, path, act, f in CASES:
    if not path.exists():
        print('MISSING', tag, path, flush=True); continue
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action if act is None else bpy.data.actions[act]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    sc.frame_set(f); bpy.context.view_layer.update()
    W = r.matrix_world; Wr = W.to_3x3()
    magbones = [b.name for b in r.pose.bones if 'Magazine' in b.name or 'magazine' in b.name]
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    mags = [o for o in sc.objects if o.type == 'MESH'
            and any(g.name in magbones for g in o.vertex_groups)]
    if not mags and tag in ('AKM', 'A762'):
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        for o in dst.objects:
            if o is not None:
                sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False; mags.append(o)
    if magbones:
        mb = magbones[0]
        restb = r.data.bones[mb].matrix_local
        D = W @ pose[mb] @ restb.inverted() @ W.inverted()
        mv = []
        for m in mags:
            if m.name.startswith('A762_R02_Magazine_'):
                mv.extend(D @ (m.matrix_world @ v.co) for v in m.data.vertices)
            else:
                mv.extend(m.matrix_world @ v.co for v in m.data.vertices)
    else:
        D = None
        mv = [m.matrix_world @ v.co for m in mags]
    c_mag, axis, _ = principal(mv) if mv else (Vector(), Vector((0, 1, 0)), 0)
    # sign the axis toward the muzzle/weapon (the receiver end sits closer to the
    # gun root), falling back to the higher end
    if magbones:
        c_gun = pose['WPN_root'].translation if 'WPN_root' in pose else r.pose.bones['hand_r'].matrix.translation
        if (c_gun - c_mag).dot(axis) < 0:
            axis = -axis
    else:
        zs = [(p.z, i) for i, p in enumerate(mv)]
        lo = min(mv, key=lambda p: (p - c_mag).dot(axis))
        hi = max(mv, key=lambda p: (p - c_mag).dot(axis))
        if hi.z < lo.z:
            axis = -axis
    P = {b.name: b.matrix.copy() for b in r.pose.bones}
    head = W @ P['thumb_01_l'].translation
    tip = W @ P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
    d = (tip - head)
    L = d.length * 1000
    dw = d.normalized()
    # rest direction of the thumb root, for a swing/twist split of the shipped pose
    info = {}
    for n in PARTS:
        pb = r.pose.bones[n]
        q = pb.matrix_basis.to_quaternion()
        sw, tw = swing_twist(q)
        info[n] = {'swing': round(sw, 1), 'twist': round(tw, 1),
                   'rot_wxyz': [round(x, 4) for x in q]}
    zseg = sum(((W @ P[n] @ Vector((0, r.data.bones[n].length, 0))).z - (W @ P[n].translation).z) for n in PARTS) * 1000
    rows[tag] = {'mag_bones': magbones, 'mag_meshes': [m.name for m in mags], 'frame': f,
                 'mag_axis_world': [round(x, 3) for x in axis],
                 'mag_extent_mm': round((max((p - c_mag).dot(axis) for p in mv) -
                                         min((p - c_mag).dot(axis) for p in mv)) * 1000, 1) if mv else None,
                 'thumb_length_mm': round(L, 1),
                 'thumb_dir_world': [round(x, 3) for x in dw],
                 'angle_thumb_vs_mag_deg': round(math.degrees(math.acos(max(-1, min(1, dw.dot(axis))))), 1),
                 'rise_z_mm': round(d.z * 1000, 1),
                 'along_axis_mm': round(d.dot(axis) * 1000, 1),
                 'rise_per_seg_mm': round(zseg, 1),
                 'segments': info}
    print('%s: mag_len %s mm  axis %s  thumb %.1f mm dir %s  angle-to-mag %.1f deg  rise %+.1f mm  along %+.1f mm'
          % (tag, rows[tag]['mag_extent_mm'], rows[tag]['mag_axis_world'], L,
             rows[tag]['thumb_dir_world'], rows[tag]['angle_thumb_vs_mag_deg'],
             rows[tag]['rise_z_mm'], rows[tag]['along_axis_mm']), flush=True)
    print('    segs %s' % json.dumps(info), flush=True)
(O / 'thumb_reference.json').write_text(json.dumps(rows, indent=1))
print('REF_OK', flush=True)
