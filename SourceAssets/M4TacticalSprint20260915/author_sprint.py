"""Author M4 one-handed tactical sprint using the accepted per-grip idle poses.

Blender --background --python author_sprint.py -- Base|Drum|Angled|Vertical|Canted|Prism
Produces editable Blender sources and animation-only FBX. Does not render or test.
"""
import ast
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Euler, Quaternion

O = Path(__file__).resolve().parent
S = O.parent
profile = sys.argv[sys.argv.index('--') + 1]
sources = {
    'Base': ('M4ContactImpact20260910/M4_Hand_MAT_Editable.blend', 'M4_idle'),
    'Drum': ('M4ContactImpact20260910/M4_Hand_MAT_Editable.blend', 'M4_idle'),
    'Angled': ('AngledForegrip20260910/WristNatural/A_M4_Foregrip_idle.blend', 'A_M4_Foregrip_idle'),
    'Vertical': ('MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend', 'A_M4_Vertical_idle.001'),
    'Canted': ('VREGripExtensions20260912/Final/m4/canted/A_M4_Canted_idle.blend', 'A_M4_Canted_idle.001'),
    'Prism': ('VREGripExtensions20260912/Final/m4/prism/A_M4_Prism_idle.blend', 'A_M4_Prism_idle.001'),
}
source, source_action = sources[profile]
dest = O / profile
(dest / 'Animations').mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(S / source))
rig = bpy.data.objects['SK_M4_Infima']
rig.data.pose_position = 'POSE'
scene = bpy.context.scene
scene.render.fps = 60
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
names = list(rest)
lr = {n: rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n] for n in names}
action = bpy.data.actions[source_action]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
idle = {b.name: b.matrix.copy() for b in rig.pose.bones}

# The UE base idle was published with 12 mm forward palm clearance; the drum
# adds another 20 mm. Those native publication offsets are not in M4_idle.
if profile in ('Base', 'Drum'):
    shift = idle['WPN_root'].to_3x3() @ Vector((0, -.032 if profile == 'Drum' else -.012, 0))
    for n in names:
        ancestor = n
        while ancestor and ancestor != 'clavicle_l':
            ancestor = parent[ancestor]
        if ancestor or n == 'ik_hand_l':
            idle[n].translation += shift

tree = ast.parse((S / 'DanWesson71520260913/author_weapon.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name == 'hand_at'], type_ignores=[]), '<full arm solver>', 'exec'))

def smooth(a, b, value):
    x = max(0., min(1., (value - a) / (b - a)))
    return x * x * (3. - 2. * x)

def turn(x, y, z):
    return Euler(tuple(math.radians(a) for a in (x, y, z)), 'XYZ').to_quaternion()

def make_pose(progress, phase=None):
    pose = {n: m.copy() for n, m in idle.items()}
    released = smooth(0., .22, progress)
    raised = smooth(.25, 1., progress)
    withdrawn = smooth(.16, .82, progress)
    loop = phase is not None
    side = math.sin(phase) if loop else 0.
    step = math.cos(2 * phase) if loop else 0.
    # M4 author coordinates: +Y forward, +X right, +Z up (metres).
    # Rotate the weapon around its bearing wrist; all weapon mechanical bones
    # and the right fingers share the same rigid delta.
    offset = Vector((.105, .085, -.015)) * raised
    offset += Vector((.007 * side, .009 * step, -.009 * step))
    rotation = Quaternion().slerp(turn(65 + 1.2 * side, -8 + 1.5 * side, -7 + .9 * step), raised)
    pivot = idle['hand_r'].translation
    delta = Matrix.Translation(pivot + offset) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
    for n in names:
        if n.startswith('WPN_'):
            pose[n] = delta @ idle[n]
    hand_at(pose, idle, 'r', delta @ idle['hand_r'])

    # Unwrap and move down/out first, then swing independently of the rifle.
    origin = idle['hand_l'].translation
    clear = origin + Vector((-.045, -.005, -.055)) * released
    # Run beside/below the camera: keep the complete hand behind the near view
    # during the stride, then recover through the original per-grip contact.
    target = Vector((-.26 - .008 * side, -.10 - .025 * side, -.36 + .010 * side))
    location = clear.lerp(target, withdrawn)
    wrist = idle['hand_l'].to_quaternion()
    wrist = wrist.slerp(turn(-20 + 5 * side, 8, -16) @ wrist, withdrawn)
    hand_at(pose, idle, 'l', Matrix.LocRotScale(location, wrist, idle['hand_l'].to_scale()))
    # Relax finger rotations through their existing local chain. Preserve bone
    # lengths and metacarpals; no individual finger translation or hand scaling.
    for n in names:
        if n.endswith('_l') and n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and '_metacarpal_' not in n:
            local = idle[parent[n]].inverted() @ idle[n]
            loc, q, scale = local.decompose()
            relaxed = q.slerp(lr[n].to_quaternion(), .52 * released)
            pose[n] = pose[parent[n]] @ Matrix.LocRotScale(loc, relaxed, scale)
    return pose

receipt = {'profile': profile, 'source': source, 'source_action': source_action,
           'coordinates': '+Y forward, +X right, +Z up; metres',
           'reference': 'Existing M4 raised sprint and PistolBV1x6AgeTEPd20260914 release/run reference',
           'status': 'Authored and exported; not rendered or tested', 'clips': {}}
for kind, end in [('Enter', 18), ('Loop', 36), ('Exit', 18)]:
    frames = [i * .5 for i in range(end * 2 + 1)]
    rows, previous = [], {}
    for frame in frames:
        t = frame / end
        # Exit follows the same pose path backwards so interrupted entry/exit
        # can reverse at the current progress without jumping to a new pose.
        pose = make_pose(1. if kind == 'Loop' else (1. - t if kind == 'Exit' else t),
                         2 * math.pi * t if kind == 'Loop' else None)
        row = {}
        for n in names:
            basis = lr[n].inverted() @ (pose[parent[n]].inverted() @ pose[n] if parent[n] else pose[n])
            loc, q, scale = basis.decompose()
            if n in previous and previous[n].dot(q) < 0:
                q.negate()
            previous[n] = q.copy()
            row[n] = (loc, q, scale)
        rows.append(row)
    action = bpy.data.actions.new(f'M4_TacticalSprint_{profile}_{kind}')
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
    scene.frame_start, scene.frame_end = 0, end
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    fbx = dest / 'Animations' / f'A_M4_TacticalSprint_{profile}_{kind}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_step=.5, bake_anim_simplify_factor=0)
    receipt['clips'][kind] = {'action': action.name, 'duration': end / 60., 'sample_rate': 120, 'fbx': str(fbx)}

rig.animation_data.action = bpy.data.actions[f'M4_TacticalSprint_{profile}_Loop']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start, scene.frame_end = 0, 36
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(dest / f'M4_TacticalSprint_{profile}_Editable.blend'))
(dest / 'authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('M4_TACTICAL_SPRINT_AUTHORED', profile, flush=True)
