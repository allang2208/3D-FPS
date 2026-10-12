"""Native-rig editable timelines for all eight variants and grip families."""
import bpy, json
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


def mat(v):
    return Matrix.LocRotScale(Vector(v[:3]), Quaternion((v[6], *v[3:6])), Vector(v[7:]))


def key(track, index):
    start = 0 if len(track['times']) == 1 else index*10
    return track['values'][start:start+10]


actions = {}
for role, spec in D['clips'].items():
    base = {t['bone']: t for t in spec['tracks']}
    for family in ['base', *D['profiles']]:
        overlay = {} if family == 'base' else {t['bone']: t for t in D['profiles'][family]['clips'][spec['path']]['tracks']}
        rows, previous = [], {}
        for frame in range(spec['frames']+1):
            world = {}
            for n in U['names']:
                m = mat(key(base[n], frame))
                if n in overlay:
                    delta = key(overlay[n], frame)
                    p, q, s = m.decompose()
                    m = Matrix.LocRotScale(p+Vector(delta[:3]), Quaternion((delta[6], *delta[3:6])) @ q, s+Vector(delta[7:]))
                world[n] = world.get(U['parents'][n], I) @ m
            author = {n: E @ Cinv @ world[n] @ Kinv[n] for n in names}
            row = {}
            for n in names:
                local = author[parents[n]].inverted() @ author[n] if parents[n] else author[n]
                p, q, s = (local_rest[n].inverted() @ local).decompose()
                if n in previous and q.dot(previous[n]) < 0:
                    q.negate()
                previous[n] = q.copy()
                row[n] = (p, q, s)
            rows.append(row)
        action = bpy.data.actions.new('A_Super90_Button_' + role + '_' + family)
        action.use_fake_user = True
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
        print('EDITABLE_LOADER_BUTTON', role, family, flush=True)
rig.animation_data.action = actions[('empty_7', 'base')]
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = D['fps'], 1
scene.frame_start, scene.frame_end = 0, D['clips']['empty_7']['frames']
scene.frame_set(0)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'Super90_Loader_ButtonRelease_Editable.blend'))
