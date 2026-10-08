"""Author anticipation, a 0.25 s burst, jaw closure and a continuous recovery.

Use the current V15 mother rig/skin and the active V08 bite as amplitude/pose
input. Only the new action is exported; no geometry or bind pose is replaced.
"""
from pathlib import Path
import json
import math
import bpy
from mathutils import Vector, Quaternion

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/SpiralPillarM14Meshy20261004'
OUT = ROOT / 'ProductionV21'
PLAN = json.loads(Path(__file__).with_name('bite_v21.json').read_text(encoding='utf8'))
for directory in ('Authoring', 'Exports', 'Records'):
    (OUT / directory).mkdir(parents=True, exist_ok=True)
source = ROOT / 'ProductionV15/Authoring/M14_SupportSkin_v15.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = bpy.data.objects['M14_Rig']
scene = bpy.context.scene
original = bpy.data.actions[PLAN['source_action']]
rig.animation_data.action = original
rig.animation_data.action_slot = original.slots[0]
scene.render.fps = 30
names = [bone.name for bone in rig.pose.bones]
axes = {bone.name: bone.bone.matrix_local.to_3x3().inverted() for bone in rig.pose.bones}

# Sample the authoring input before inserting any keys into the new action.
# V08 stores half-frame keys in the mother's original 30 Hz time base.
samples = []
for index in range(58):
    source_frame = index * .5
    scene.frame_set(math.floor(source_frame), subframe=source_frame % 1.)
    samples.append({bone.name: (bone.location.copy(), bone.rotation_quaternion.copy(), bone.scale.copy())
                    for bone in rig.pose.bones})
rest_axes = rig.pose.bones['maw'].bone.matrix_local.to_3x3()
peak_index = max(range(len(samples)), key=lambda i: -(rest_axes @ samples[i]['maw'][0]).y)
maw_start = samples[0]['maw'][0]
maw_peak = samples[peak_index]['maw'][0]
jaw_open = {name: max((sample[name][0] for sample in samples), key=lambda pos: pos.length_squared).copy()
            for name in names if name.startswith('jaw_')}

def clamp(value):
    return max(0., min(1., value))

def ease(value):
    q = clamp(value)
    return q * q * (3. - 2. * q)

def burst(value):
    # Slow release, late acceleration, then zero velocity at full reach.
    q = clamp(value)
    return q ** 3 * (4. - 3. * q)

def pulse(t, start, peak, end):
    return ease((t - start) / (peak - start)) if t < peak else 1. - ease((t - peak) / (end - peak))

def curve(t, keys):
    for (ta, va), (tb, vb) in zip(keys, keys[1:]):
        if t <= tb:
            return va + (vb - va) * ease((t - ta) / (tb - ta))
    return keys[-1][1]

def source_pose(seconds, name):
    frame = max(0., min(57., seconds * 60.))
    lo, hi = int(frame), min(57, int(frame) + 1)
    q = frame - lo
    a, b = samples[lo][name], samples[hi][name]
    return a[0].lerp(b[0], q), a[1].slerp(b[1], q), a[2].lerp(b[2], q)

def turn(name, axis, radians):
    bone = rig.pose.bones[name]
    bone.rotation_quaternion = Quaternion(axes[name] @ Vector(axis), radians) @ bone.rotation_quaternion

anticipate = PLAN['anticipation_end_seconds']
extend = PLAN['maximum_extension_seconds']
contact = PLAN['contact_seconds']
recoil = PLAN['recoil_start_seconds']
recover = PLAN['recovery_start_seconds']
duration = PLAN['duration_seconds']
fraction = PLAN['anticipation_extension_fraction']
fps = PLAN['export_fps']
frames = round(duration * fps)
action = bpy.data.actions.new(PLAN['action'])
action.use_fake_user = True
rig.animation_data.action = action
scene.render.fps = fps
scene.frame_start, scene.frame_end = 0, frames
for frame in range(frames + 1):
    t = frame / fps
    scene.frame_set(frame)
    # Retain the original whole-body anticipation and tissue follow-through.
    source_time = curve(t, [(0., 0.), (anticipate, .275), (extend, .43),
                            (recoil, .43), (.94, .515), (1.16, .72), (duration, .95)])
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        bone.location, bone.rotation_quaternion, bone.scale = source_pose(source_time, bone.name)
    if t <= anticipate:
        extension = fraction * ease(t / anticipate)
    elif t <= extend:
        extension = fraction + (1. - fraction) * burst((t - anticipate) / (extend - anticipate))
    elif t <= recoil:
        extension = 1.
    else:
        extension = curve(t, [(recoil, 1.), (.90, .90), (recover, .915), (duration, 0.)])
    rig.pose.bones['maw'].location = maw_start.lerp(maw_peak, extension)
    # Hold an open mouth through the burst; close in three 60 Hz frames at
    # maximum reach. Never blend the gape down throughout the entire lunge.
    gape = curve(t, [(0., 0.), (anticipate, .82), (.68, 1.), (extend, 1.),
                     (contact, PLAN['jaw_clench_fraction']), (.87, PLAN['jaw_clench_fraction']),
                     (.98, .10), (1.16, .04), (duration, 0.)])
    for name, opening in jaw_open.items():
        rig.pose.bones[name].location = opening * gape
    # Small recoil travels through the body, then the hanging sacs, with no
    # root translation or extra reach beyond the existing mouth peak.
    for k in range(2, 6):
        lag = (k - 2) * .012
        turn(f'spine_{k:02d}', (1, 0, 0), -.012 * pulse(t, contact + lag, .89 + lag, 1.22 + lag))
    for side, lag in (('L', .018), ('R', .038)):
        turn('sac_' + side, (1, 0, 0), .025 * pulse(t, contact + lag, .97 + lag, 1.36 + lag))
    for bone in rig.pose.bones:
        bone.keyframe_insert('location', frame=frame, group=bone.name)
        bone.keyframe_insert('rotation_quaternion', frame=frame, group=bone.name)
        bone.keyframe_insert('scale', frame=frame, group=bone.name)

def channels():
    for slot in action.slots:
        for layer in action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(slot)
                if bag:
                    yield from bag.fcurves

# Nonlinear motion is densely baked; linear interpolation between these
# samples avoids spline overshoot at the three-frame jaw closure.
for channel in channels():
    for key in channel.keyframe_points:
        key.interpolation = 'LINEAR'
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
export = OUT / 'Exports' / (PLAN['action'] + '.fbx')
bpy.ops.export_scene.fbx(filepath=str(export), object_types={'ARMATURE'}, use_selection=True,
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y',
    add_leaf_bones=False, use_armature_deform_only=True, armature_nodetype='NULL', path_mode='STRIP',
    use_mesh_modifiers=False, bake_anim=True, bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0.)
for channel in channels():
    for key in channel.keyframe_points:
        key.co.x *= 30. / fps
        key.handle_left.x *= 30. / fps
        key.handle_right.x *= 30. / fps
scene.render.fps = 30
scene.frame_end = max(72, round(duration * 30))
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.location = (0, 0, 0)
    bone.rotation_quaternion = (1, 0, 0, 0)
    bone.scale = (1, 1, 1)
scene.frame_set(0)
blend = OUT / 'Authoring/M14_StagedBite_v21.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
report = dict(PLAN, source_blend=str(source), blend=str(blend), bite_fbx=str(export),
              source_peak_outward_cm=-(rest_axes @ maw_peak).y * 100.,
              source_peak_frame_60hz=peak_index, contact_frame_60hz=round(contact * fps),
              geometry_skin_and_other_actions_preserved=True, native_code_changed=False,
              tested=False, rendered=False)
(OUT / 'Records/authoring.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print('M14_V21_BITE_AUTHORED ' + json.dumps(report), flush=True)
