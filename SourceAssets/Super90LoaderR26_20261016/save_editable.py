"""Native-rig editable timelines for the fourteen R26 loader clips and four grip families.

Run: blender -b --factory-startup --python save_editable.py
Opens the R24 editable rig without its scripts and writes one action per clip/family.
"""
import bpy, json, bisect
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

O = Path(__file__).parent
D = json.loads((O / 'animation_patch.json').read_text())
U = json.loads((O / 'inputs.json').read_text())
A = json.loads((O.parent / 'Super90QuickMelee20261008/LeftArmR5/author_space.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(O.parent / 'Super90LoaderR24_20261010/Super90_Speedloader_R24.blend'), use_scripts=False)
rig = bpy.data.objects['SK_Super90']
rig.data.pose_position = 'POSE'
I = Matrix.Identity(4)
Cinv, E = Matrix(A['conversion']['C']).inverted(), Matrix(A['conversion']['E'])
Kinv = {n: Matrix(m).inverted() for n, m in A['conversion']['K'].items()}
rest = {n: Matrix(m) for n, m in A['rest'].items()}
parents, names = A['parents'], A['names']
local_rest = {n: rest[parents[n]].inverted() @ m if parents[n] else m for n, m in rest.items()}


def split(v):
    return Vector(v[:3]), Quaternion((v[6], *v[3:6])), Vector(v[7:10])


def sample(track, t):
    times, values = track['times'], track['values']
    if len(times) == 1 or t <= times[0]:
        return split(values[:10])
    if t >= times[-1]:
        return split(values[-10:])
    hi = bisect.bisect_right(times, t); lo = hi - 1
    u = (t - times[lo]) / (times[hi] - times[lo])
    a, b = split(values[lo * 10:lo * 10 + 10]), split(values[hi * 10:hi * 10 + 10])
    return a[0].lerp(b[0], u), a[1].slerp(b[1], u), a[2].lerp(b[2], u)


actions = {}
for role, spec in D['clips'].items():
    clip = U['clips'][role]
    written = {t['bone']: t for t in spec['tracks']}
    for family in ['base', *D['profiles']]:
        overlay = [] if family == 'base' else D['profiles'][family]['clips'][spec['path']]['tracks']
        rows, previous = [], {}
        for frame, t in enumerate(clip['times']):
            local = {}
            for n in U['names']:
                p, q, s = sample(written[n], t) if n in written else split(clip['rows'][frame][n])
                local[n] = [p, q, s]
            for track in overlay:
                dp, dq, ds = sample(track, t)
                item = local[track['bone']]
                item[0], item[1], item[2] = item[0] + dp, dq @ item[1], item[2] + ds
            world = {}
            for n in U['names']:
                p, q, s = local[n]
                world[n] = world.get(U['parents'][n], I) @ Matrix.LocRotScale(p, q, s)
            author = {n: E @ Cinv @ world[n] @ Kinv[n] for n in names}
            row = {}
            for n in names:
                m = author[parents[n]].inverted() @ author[n] if parents[n] else author[n]
                p, q, s = (local_rest[n].inverted() @ m).decompose()
                if n in previous and q.dot(previous[n]) < 0:
                    q.negate()
                previous[n] = q.copy()
                row[n] = (p, q, s)
            rows.append(row)
        action = bpy.data.actions.new('A_Super90_LoaderR26_' + role + '_' + family)
        action.use_fake_user = True
        rig.animation_data_create()
        rig.animation_data.action = action
        for bone in rig.pose.bones:
            bone.rotation_mode = 'QUATERNION'
            for prop in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(prop, frame=0)
        curves = {(c.data_path, c.array_index): c for layer in action.layers for strip in layer.strips
                  for bag in strip.channelbags for c in bag.fcurves}
        for n in names:
            for prop, field, count in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
                for axis in range(count):
                    curve = curves[(f'pose.bones["{n}"].{prop}', axis)]
                    curve.keyframe_points.clear()
                    curve.keyframe_points.add(len(rows))
                    curve.keyframe_points.foreach_set('co', [v for i, row in enumerate(rows) for v in (i, row[n][field][axis])])
                    for point in curve.keyframe_points:
                        point.interpolation = 'LINEAR'
                    curve.update()
        actions[(role, family)] = action
        print('EDITABLE_LOADER_R26', role, family, flush=True)
rig.animation_data.action = actions[('normal_7', 'base')]
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = D['fps'], 1
scene.frame_start, scene.frame_end = 0, D['clips']['normal_7']['frames']
scene.frame_set(0)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'Super90_Loader_R26_Editable.blend'))
print('EDITABLE_LOADER_R26_SAVED', len(actions), flush=True)
