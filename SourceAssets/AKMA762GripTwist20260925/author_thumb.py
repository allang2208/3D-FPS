"""Re-author the thumb tracks of the shipped AKM / A762 magazine-grip reloads.

The shipped grip rolls ``thumb_01_l`` about its own axis by ~67 deg and leaves the
thumb pad 12-15 mm off the shell, which reads as a twisted, flat thumb.  Following
the accepted SVD reload repair, only the three thumb rotation tracks are replaced:
the root is a swing-only rotation (no twist about the thumb axis) aimed at the
magazine, the two distal segments keep a light flexion, and everything else - palm,
four fingers, wrist, fore arm, magazine track, weapon, cues and clip length - is
untouched.

Blend schedule follows the documented grip edit window: 20 -> 44 close, hold to
237, 237 -> 250 open back into the clip's own return track.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

O = Path(__file__).parent; S = O.parent
BONES = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
CLOSE = (20.0, 44.0)
OPEN = (237.0, 250.0)


def smooth(x):
    t = max(0.0, min(1.0, x))
    return t * t * (3 - 2 * t)


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


def target_quats(params):
    a, b, c, d = params
    return {
        'thumb_01_l': swing_only(Matrix.Rotation(math.radians(a), 4, 'Z').to_quaternion() @
                                 Matrix.Rotation(math.radians(b), 4, 'X').to_quaternion()),
        'thumb_02_l': Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion(),
        'thumb_03_l': Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion(),
    }


def twist_of(q):
    q = q.copy(); q.normalize()
    a = Vector((0.0, 1.0, 0.0))
    p = a * Vector((q.x, q.y, q.z)).dot(a)
    if p.length < 1e-12:
        return 0.0
    tw = math.degrees(2.0 * math.atan2(p.length, q.w))
    return -tw if p.dot(a) < 0 else tw


fit = json.loads((O / 'thumb_fit.json').read_text())
SOURCES = json.loads((S / 'RifleMagazineGrip20260922/IndexClearanceV4/sources.json').read_text())['animations']
TARGET = {}
for gun in ('AKM', 'A762'):
    p = fit[gun]['params']
    TARGET[gun] = target_quats([p['a_z'], p['b_x'], p['c_02'], p['d_03']])

V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
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
    curves = {(fc.data_path, fc.array_index): fc for la in act.layers for st in la.strips
              for bag in st.channelbags for fc in bag.fcurves}
    tq = TARGET[gun]
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
        i0 = max(range(len(before)), key=lambda i: abs(before[i]))
        i1 = max(range(len(after)), key=lambda i: abs(after[i]))
        stats[n] = {'twist_before': round(before[i0], 2), 'twist_after': round(after[i1], 2)}
    step = float(fc[0].keyframe_points[1].co.x - fc[0].keyframe_points[0].co.x)
    out = O / gun / magaz / family
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
    receipt[key] = {'asset': job['asset'], 'source_blend': str(src), 'blend': str(out / (stem + '.blend')),
                    'fbx': str(out / (stem + '.fbx')), 'fps': 120, 'sample_step': step,
                    'thumb_target': {k: [round(x, 5) for x in v] for k, v in tq.items()},
                    'twist': stats, 'changed_bones': BONES, 'updated_receipt': 'AKMA762GripTwist20260925'}
    (O / 'authoring.json').write_text(json.dumps(receipt, indent=1), encoding='utf-8')
    print('THUMB_AUTHORED', key, json.dumps(stats), flush=True)
print('THUMB_AUTHOR_OK', len(receipt), flush=True)
