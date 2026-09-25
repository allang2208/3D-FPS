"""Verify the thumb re-authoring: only the three thumb tracks changed, their root
twist is gone, and the thumb pad now sits on the magazine shell."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
BONES = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
PAD = ['thumb_02_l', 'thumb_03_l']
CHECK = ['hand_l', 'index_01_l', 'index_02_l', 'index_03_l', 'middle_01_l', 'middle_02_l', 'middle_03_l',
         'ring_01_l', 'ring_02_l', 'ring_03_l', 'pinky_01_l', 'pinky_02_l', 'pinky_03_l',
         'lowerarm_l', 'upperarm_l', 'clavicle_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l',
         'upperarm_twist_01_l', 'upperarm_twist_02_l']
V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'


def twist_of(q):
    q = q.copy(); q.normalize()
    a = Vector((0.0, 1.0, 0.0))
    p = a * Vector((q.x, q.y, q.z)).dot(a)
    if p.length < 1e-12:
        return 0.0
    tw = math.degrees(2.0 * math.atan2(p.length, q.w))
    return -tw if p.dot(a) < 0 else tw


def analyse(path, action, frames):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action if action is None else bpy.data.actions[action]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects.get('SK_Manny_Arms_Export')
    sc = bpy.context.scene
    rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
    parents = {b.name: (b.parent.name if b.parent else None) for b in r.data.bones}
    out = {}
    for f in frames:
        sc.frame_set(int(f), subframe=f % 1); bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        pose = {b.name: b.matrix.copy() for b in r.pose.bones}
        rec = {'twist': {}, 'basis': {}}
        for n in BONES:
            p = parents[n]
            rr = rest[p].inverted() @ rest[n]
            pr = pose[p].inverted() @ pose[n]
            rec['twist'][n] = round(twist_of((rr.inverted() @ pr).to_quaternion()), 2)
        for n in CHECK:
            if n in pose:
                rec['basis'][n] = list(pose[n].to_quaternion())
        if arms is not None:
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
            tree = BVHTree.FromPolygons(mv, mp, all_triangles=False)
            e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
            groups = [g.name for g in arms.vertex_groups]
            acc = {p: [] for p in PAD}
            for v in me.vertices:
                best, w = None, 0.0
                for g in v.groups:
                    if g.weight > w:
                        best, w = groups[g.group], g.weight
                if best in acc:
                    acc[best].append(M @ v.co)
            e.to_mesh_clear()
            pad = {}
            for p, pts in acc.items():
                d = []
                for q in pts:
                    loc, nor, _, dist = tree.find_nearest(q)
                    if loc is None:
                        continue
                    d.append(-dist * 1000 if (q - loc).dot(nor) < 0 else dist * 1000)
                d.sort()
                pad[p] = {'min': round(d[0], 2), 'med': round(d[len(d) // 2], 2)}
            rec['pad'] = pad
        out[str(f)] = rec
    return out


SOURCES = json.loads((V4 / 'sources.json').read_text())['animations']
report = {}
for job in SOURCES:
    key = '/'.join((job['gun'], job['magazine'], job['family'], job['clip']))
    stem = Path(job['asset']).name
    old = V4 / job['gun'] / job['magazine'] / job['family'] / (stem + '.blend')
    new = O / job['gun'] / job['magazine'] / job['family'] / (stem + '.blend')
    if not new.exists():
        print('MISSING', new, flush=True); continue
    frames = [148]
    a_old = analyse(old, None, frames)
    a_new = analyse(new, None, frames)
    f = str(frames[0])
    moved = {n: round(math.degrees(Quaternion(a_old[f]['basis'][n]).rotation_difference(
        Quaternion(a_new[f]['basis'][n])).angle), 4) for n in a_old[f]['basis']}
    worst = max(moved.values()) if moved else 0.0
    report[key] = {'non_thumb_max_move_deg': worst,
                   'thumb_twist_before': a_old[f]['twist'], 'thumb_twist_after': a_new[f]['twist'],
                   'pad_before': a_old[f]['pad'], 'pad_after': a_new[f]['pad']}
    print('%-26s others<=%.4f deg | twist %s -> %s | pad %s -> %s' % (
        key, worst,
        {k.replace('_l', ''): v for k, v in a_old[f]['twist'].items()},
        {k.replace('_l', ''): v for k, v in a_new[f]['twist'].items()},
        {k.replace('_l', ''): v['med'] for k, v in a_old[f]['pad'].items()},
        {k.replace('_l', ''): v['med'] for k, v in a_new[f]['pad'].items()}), flush=True)
(O / 'verify_thumb.json').write_text(json.dumps(report, indent=1))
print('VERIFY_THUMB_OK', len(report), flush=True)
