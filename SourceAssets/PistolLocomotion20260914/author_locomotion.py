"""Author pistol sprint cycles from the current per-weapon idle contacts.

Run with Blender --background --python author_locomotion.py -- M1911|DW715.
Creates editable source and FBX only; no render, tests or gameplay launch.
"""
import ast
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector, Euler

O = Path(__file__).parent
S = O.parent
config = json.loads((O / 'motion.json').read_text(encoding='utf-8'))
weapon = sys.argv[sys.argv.index('--') + 1]
spec = config['weapons'][weapon]
dest = O / weapon
(dest / 'Animations').mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
try:
    bpy.ops.wm.open_mainfile(filepath=str(S / spec['source']))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):
        raise
rig = bpy.data.objects[spec['rig']]
rig.data.pose_position = 'POSE'
scene = bpy.context.scene
scene.render.fps = 60
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
names = list(rest)
lr = {n: rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n] for n in names}

# Reuse the current 715 full-arm solver (including complete twist bone motion).
# Execute just this authoring function, never its mesh/material setup code.
tree = ast.parse((S / 'DanWesson71520260913/author_weapon.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name == 'hand_at'], type_ignores=[]), '<pistol arm solve>', 'exec'))

def camera_vector(value):
    # P9/Manny author basis: Blender -Y forward, -X camera-right, +Z up.
    return Vector((-value[1], -value[0], value[2]))

def camera_turn(pitch, yaw, roll):
    return Euler(tuple(math.radians(a) for a in (-pitch, -roll, -yaw)), 'XYZ').to_quaternion()

def sample_idle(action_name):
    action = bpy.data.actions[action_name]
    rig.animation_data_create()
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(0)
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}

duration = config['cycle_seconds']
frames = [i * 60 / config['sample_rate'] for i in range(round(duration * config['sample_rate']) + 1)]
receipt = {'weapon': weapon, 'source': spec['source'], 'clips': {},
           'state': 'Authored and exported; not tested or rendered'}
for kind, source_name in spec['idle_actions'].items():
    idle = sample_idle(source_name)
    rows = []
    previous = {}
    for frame in frames:
        phase = 2 * math.pi * frame / (duration * 60)
        side = math.cos(phase)
        step = math.cos(2 * phase)
        wrist = math.cos(phase - .32)
        center, amp = spec['gun_center_m'], spec['gun_amplitude_m']
        offset = camera_vector((center[0] + amp[0] * math.sin(2 * phase - .25),
                                center[1] + amp[1] * side,
                                center[2] - amp[2] * step))
        angle, angular = spec['gun_center_pitch_yaw_roll'], spec['gun_amplitude_pitch_yaw_roll']
        rotation = camera_turn(angle[0] + angular[0] * math.sin(phase - .20),
                               angle[1] + angular[1] * wrist,
                               angle[2] - angular[2] * math.sin(phase - .32))
        # Pivot at the right wrist, so lateral gun motion does not orbit the rig origin.
        pivot = idle['hand_r'].translation
        delta = Matrix.Translation(pivot + offset) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
        pose = {n: m.copy() for n, m in idle.items()}
        for n in names:
            if n.startswith('WPN_'):
                pose[n] = delta @ idle[n]
        hand_at(pose, idle, 'r', delta @ idle['hand_r'])

        # The support hand moves independently in view space after releasing the grip.
        # Its stride opposes the gun-bearing arm; do not apply the gun-root turn here.
        release, swing = spec['left_release_m'], spec['left_amplitude_m']
        left_offset = camera_vector((release[0] - swing[0] * side,
                                     release[1] - swing[1] * math.sin(phase),
                                     release[2] + swing[2] * math.sin(phase - .25)))
        hand = idle['hand_l'].copy()
        hand = Matrix.LocRotScale(hand.translation + left_offset,
                                 camera_turn(-12 - 4 * side, -8, 10) @ hand.to_quaternion(),
                                 hand.to_scale())
        hand_at(pose, idle, 'l', hand)
        row = {}
        for n in names:
            basis = lr[n].inverted() @ (pose[parent[n]].inverted() @ pose[n] if parent[n] else pose[n])
            loc, q, scale = basis.decompose()
            if n in previous and previous[n].dot(q) < 0:
                q.negate()
            previous[n] = q.copy()
            row[n] = (loc, q, scale)
        rows.append(row)

    action = bpy.data.actions.new(f'{weapon}_Locomotion_{kind}')
    action.use_fake_user = True
    rig.animation_data.action = action
    for n in names:
        bone = rig.pose.bones[n]
        bone.rotation_mode = 'QUATERNION'
        for prop in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(prop, frame=0)
    curves = {(c.data_path, c.array_index): c for c in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves}
    for n in names:
        for prop, field, count in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
            for axis in range(count):
                curve = curves[(f'pose.bones["{n}"].{prop}', axis)]
                curve.keyframe_points.clear()
                curve.keyframe_points.add(len(frames))
                curve.keyframe_points.foreach_set('co', [v for f, row in zip(frames, rows) for v in (f, row[n][field][axis])])
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
                curve.update()
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_start = 0
    scene.frame_end = round(duration * 60)
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    fbx = dest / 'Animations' / f'A_{weapon}_{kind}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
                            axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
                            bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                            bake_anim_force_startend_keying=True, bake_anim_step=.5, bake_anim_simplify_factor=0)
    receipt['clips'][kind] = {'source_action': source_name, 'action': action.name,
                             'duration': duration, 'sample_rate': config['sample_rate'], 'fbx': str(fbx)}

# Pack existing maps so saving in a new folder does not break the editable scene.
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(dest / f'{weapon}_Locomotion_Editable.blend'))
(dest / 'authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('PISTOL_LOCOMOTION_AUTHORED', weapon, flush=True)
