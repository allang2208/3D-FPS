"""Re-author the 30 AKM / A762 magazine-grip reload thumbs so the thumb extends
naturally, without touching the web.

The v1 pass removed the ~67 deg roll about the thumb axis; v2 then swung the root
73-78 deg further to lay the thumb along the magazine, which dragged the skin
between thumb and index and read as a wrongly stretched web (web gap +33 %,
62-65 mm of web skin moved).  The SVD repair already accepted in this project
does the opposite: the root stays a few degrees from the base pose and the thumb
extends because the two distal segments are left almost straight.

So this pass changes nothing at the root - it keeps the root that is shipping
(thumb_target3.json reproduces the round-1 receipt exactly) - and only replaces
the distal flexion, 30/25 deg (AKM) and 33.5/34.8 (A762), with the SVD's light
4/3 deg.  Visible thumb goes 55.5 / 53.3 mm (87 % / 84 % of rest) to 63.3 / 63.7
mm (99.6 % / 100.2 %); the web gap moves 54.73 -> 54.62 mm and 57.18 -> 57.06 mm,
and the web skin moves 2.9 / 3.2 mm against the shipping pose.

Outputs go to v3/<gun>/<magazine>/<family>/ so the earlier rounds stay in place.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

O = Path(__file__).parent; S = O.parent
V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
BONES = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
CLOSE = (20.0, 44.0)
OPEN = (237.0, 250.0)
TARGET = json.loads((O / 'thumb_target3.json').read_text())


def smooth(x):
    t = max(0.0, min(1.0, x))
    return t * t * (3 - 2 * t)


def twist_of(q):
    q = q.copy(); q.normalize()
    a = Vector((0.0, 1.0, 0.0))
    p = a * Vector((q.x, q.y, q.z)).dot(a)
    if p.length < 1e-12:
        return 0.0
    tw = math.degrees(2.0 * math.atan2(p.length, q.w))
    return -tw if p.dot(a) < 0 else tw


def target_quats(gun):
    t = TARGET[gun]
    return {'thumb_01_l': Quaternion(t['root_quat_wxyz']),
            'thumb_02_l': Matrix.Rotation(math.radians(t['c_02']), 4, 'Z').to_quaternion(),
            'thumb_03_l': Matrix.Rotation(math.radians(t['d_03']), 4, 'Z').to_quaternion()}


SOURCES = json.loads((V4 / 'sources.json').read_text())['animations']
receipt = {}
for job in SOURCES:
    gun, magaz, family, clip = job['gun'], job['magazine'], job['family'], job['clip']
    stem = Path(job['asset']).name
    src = V4 / gun / magaz / family / (stem + '.blend')
    if not src.exists():
        print('MISSING', src, flush=True)
        continue
    bpy.ops.wm.open_mainfile(filepath=str(src), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    sc = bpy.context.scene
    act = r.animation_data.action
    r.animation_data.action_slot = act.slots[0]
    sc.frame_set(148); bpy.context.view_layer.update()
    before_all = {b.name: b.matrix_basis.to_quaternion().copy() for b in r.pose.bones}
    curves = {(fc.data_path, fc.array_index): fc for la in act.layers for st in la.strips
              for bag in st.channelbags for fc in bag.fcurves}
    tq = target_quats(gun)
    stats = {}
    for n in BONES:
        fc = [curves.get(('pose.bones["%s"].rotation_quaternion' % n, i)) for i in range(4)]
        if any(c is None for c in fc):
            raise RuntimeError('missing channel ' + n)
        before, after = [], []
        prev = None
        for i, k in enumerate(fc[0].keyframe_points):
            f = float(k.co.x)
            q = Quaternion([c.keyframe_points[i].co.y for c in fc])
            before.append(twist_of(q))
            w = smooth((f - CLOSE[0]) / (CLOSE[1] - CLOSE[0])) * (1.0 - smooth((f - OPEN[0]) / (OPEN[1] - OPEN[0])))
            if w > 0:
                q = q.slerp(tq[n], w)
            if prev is not None and prev.dot(q) < 0:
                q.negate()
            prev = q.copy()
            after.append(twist_of(q))
            for axis, c in enumerate(fc):
                c.keyframe_points[i].co.y = q[axis]
                c.keyframe_points[i].interpolation = 'LINEAR'
        for c in fc:
            c.update()
        i1 = max(range(len(after)), key=lambda i: abs(after[i]))
        i0 = max(range(len(before)), key=lambda i: abs(before[i]))
        stats[n] = {'twist_before_max': round(before[i0], 2), 'twist_after_max': round(after[i1], 2),
                    'keys': len(after)}
    # the edit must move nothing but the three thumb tracks
    sc.frame_set(148); bpy.context.view_layer.update()
    moved = {}
    for b in r.pose.bones:
        q = b.matrix_basis.to_quaternion()
        d = before_all[b.name].rotation_difference(q)
        ang = math.degrees(d.angle)
        if ang > 1e-4:
            moved[b.name] = round(ang, 4)
    step = float(fc[0].keyframe_points[1].co.x - fc[0].keyframe_points[0].co.x)
    out = O / 'v3' / gun / magaz / family
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    r.hide_set(False); r.select_set(True); bpy.context.view_layer.objects.active = r
    sc.frame_set(148)
    bpy.ops.export_scene.fbx(filepath=str(out / (stem + '.fbx')), use_selection=True,
                             object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z',
                             add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                             bake_anim_step=step, bake_anim_simplify_factor=0)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / (stem + '.blend')))
    key = '/'.join((gun, magaz, family, clip))
    receipt[key] = {'asset': job['asset'], 'source_blend': str(src),
                    'blend': str(out / (stem + '.blend')), 'fbx': str(out / (stem + '.fbx')),
                    'fps': 120, 'sample_step': step,
                    'thumb_target': {k: [round(x, 6) for x in v] for k, v in tq.items()},
                    'twist': stats, 'moved_bones': moved, 'changed_bones': BONES,
                    'round1_target': json.loads((O / 'thumb_fit.json').read_text())[gun]['params'],
                    'basis': 'v2 upward extension of the round-1 twist repair'}
    (O / 'authoring3.json').write_text(json.dumps(receipt, indent=1), encoding='utf-8')
    print('THUMB2_AUTHORED %-42s moved=%s twist_after=%s' %
          (key, json.dumps(moved), json.dumps({k: v['twist_after_max'] for k, v in stats.items()})), flush=True)
print('THUMB2_AUTHOR_OK', len(receipt), flush=True)
