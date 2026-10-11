"""Store native walk/run patches as ten editable V7 Blender actions."""
import bpy
import json
import bisect
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
P = json.loads((O / 'animation_patch.json').read_text())
A = json.loads((O.parent / 'Super90QuickMelee20261008/LeftArmR5/author_space.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(O.parent / 'Super90QuickMelee20261008/RightArmR9/Super90_QuickMelee_Editable.blend'), use_scripts=False)
rig = bpy.data.objects['SK_Super90']
I = Matrix.Identity(4)
Cinv, E = Matrix(A['conversion']['C']).inverted(), Matrix(A['conversion']['E'])
Kinv = {n: Matrix(m).inverted() for n, m in A['conversion']['K'].items()}
rest = {n: Matrix(m) for n, m in A['rest'].items()}
local_rest = {n: rest[A['parents'][n]].inverted() @ m if A['parents'][n] else m for n, m in rest.items()}


def quat(v):
    return Quaternion((v[6], *v[3:6]))


def sample(t, time):
    ts, data = t['times'], t['values']
    hi = bisect.bisect_right(ts, time)
    if hi == 0:
        return data[:10]
    if hi == len(ts):
        return data[-10:]
    lo = hi - 1
    a, b = data[lo * 10:(lo + 1) * 10], data[hi * 10:(hi + 1) * 10]
    f = (time - ts[lo]) / (ts[hi] - ts[lo])
    v = [(1 - f) * x + f * y for x, y in zip(a, b)]
    q = quat(a).slerp(quat(b), f)
    v[3:7] = [q.x, q.y, q.z, q.w]
    return v


actions = {}
for role, source in D['clips'].items():
    if role == 'idle':
        continue
    patch = {t['bone']: t for t in P['clips'][role]['tracks']}
    for family in ('base', *D['profiles']):
        layers = []
        if family != 'base':
            layers = [t for t in D['profiles'][family]['clips'][source['path']]['tracks'] if t['bone'] not in P['right_bones']]
            layers += P['profiles'][family]['clips'][source['path']]['tracks']
        rows, previous = [], {}
        for time, native in zip(source['times'], source['rows']):
            local = {n: list(v) for n, v in native.items()}
            for n, t in patch.items():
                local[n] = sample(t, time)
            for t in layers:
                v, d = local[t['bone']], sample(t, time)
                q = quat(d) @ quat(v)
                local[t['bone']] = [v[i] + d[i] for i in range(3)] + [q.x, q.y, q.z, q.w] + [v[i] + d[i] for i in range(7, 10)]
            world = {}
            for n in D['names']:
                v = local[n]
                world[n] = world.get(D['parents'][n], I) @ Matrix.LocRotScale(Vector(v[:3]), quat(v), Vector(v[7:]))
            author = {n: E @ Cinv @ world[n] @ Kinv[n] for n in A['names']}
            row = {}
            for n in A['names']:
                parent = A['parents'][n]
                l = author[parent].inverted() @ author[n] if parent else author[n]
                pos, q, scale = (local_rest[n].inverted() @ l).decompose()
                if n in previous and q.dot(previous[n]) < 0:
                    q.negate()
                previous[n] = q.copy()
                row[n] = pos, q, scale
            rows.append(row)
        action = bpy.data.actions.new('A_Super90_' + role + '_IdleRightGrip_' + family)
        action.use_fake_user = True
        rig.animation_data.action = action
        for bone in rig.pose.bones:
            bone.rotation_mode = 'QUATERNION'
            for prop in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(prop, frame=0)
        curves = {(c.data_path, c.array_index): c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
        for n in A['names']:
            for prop, field, count in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
                for axis in range(count):
                    curve = curves[(f'pose.bones["{n}"].{prop}', axis)]
                    curve.keyframe_points.clear()
                    curve.keyframe_points.add(len(rows))
                    curve.keyframe_points.foreach_set('co', [v for i, row in enumerate(rows) for v in (source['times'][i] * 60, row[n][field][axis])])
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
                    curve.update()
        actions[(role, family)] = action
        print('EDITABLE_LOCOMOTION_ACTION', role, family, flush=True)
rig.animation_data.action = actions[('walk', 'base')]
rig.animation_data.action_slot = actions[('walk', 'base')].slots[0]
bpy.context.scene.render.fps = 60
bpy.context.scene.render.fps_base = 1
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = D['clips']['walk']['frames']
bpy.context.scene.frame_set(0)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'Super90_Locomotion_IdleGrip_Editable.blend'))
