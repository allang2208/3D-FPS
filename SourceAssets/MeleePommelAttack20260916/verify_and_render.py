"""Delivery numbers and review frames for A_RuneSword_PommelStrike.

Numbers: idle endpoint continuity, hilt-contact invariance, elbow bend, the
counterweight path, and how far the blade stays from the aiming line.
Frames: first-person and three-quarter views at the authored phase times.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

P = Path(__file__).parent
REVIEW = P / 'Review'
REVIEW.mkdir(exist_ok=True)
FPS = 480
BLEND = P / 'AzureRunesword_PommelStrikeV46.blend'
CLIP = 'A_RuneSword_PommelStrike'
BUTT_M = 0.27
EYE = Vector((0, 0, 0))
FP_SHOTS = [0.00, 0.20, 0.40, 0.58, 0.72, 0.84, 0.88, 0.92, 0.98, 1.14, 1.60]
JOINT_SHOTS = [0.40, 0.58, 0.72, 0.92, 1.14]

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
blade = bpy.data.objects['RuneSword_Blade']


def pose_map():
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def set_time(action, seconds):
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    frame = seconds * FPS
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return pose_map()


pommel = bpy.data.actions[CLIP]
# The authored blends keep no separate idle action: every attack clip starts and
# ends on the same ready pose, so Slash1's first frame is the idle reference here.
idle = bpy.data.actions['A_RuneSword_Slash1']

idle_pose = set_time(idle, 0.0)
start_pose = set_time(pommel, 0.0)
end_pose = set_time(pommel, 1.60)
report = {'source': str(BLEND), 'clip': CLIP}


def max_delta(a, b):
    return max((a[n].translation - b[n].translation).length for n in a) * 1000.0


report['idle_start_delta_mm'] = max_delta(start_pose, idle_pose)
report['idle_end_delta_mm'] = max_delta(end_pose, idle_pose)

# Hand contacts relative to the hilt must match the accepted ready pose exactly.
for side in ('l', 'r'):
    hand = 'hand_' + side
    ref = idle_pose['WPN_root'].inverted() @ idle_pose[hand]
    values = []
    for seconds in [s / 10.0 for s in range(0, 14)]:
        pose = set_time(pommel, seconds)
        grip = pose['WPN_root'].inverted() @ pose[hand]
        values.append(((grip.translation - ref.translation).length * 1000.0,
                       math.degrees(grip.to_quaternion().rotation_difference(ref.to_quaternion()).angle)))
    report['grip_' + side] = {
        'max_offset_mm': max(v[0] for v in values),
        'max_rotation_deg': max(v[1] for v in values),
    }

rows = []
for seconds in FP_SHOTS:
    pose = set_time(pommel, seconds)
    hilt = pose['WPN_root'].translation
    blade_axis = (pose['Blade_Tip'].translation - pose['Blade_Base'].translation).normalized()
    head = hilt - blade_axis * BUTT_M
    tip = pose['Blade_Tip'].translation
    left = math.degrees((pose['lowerarm_l'].translation - pose['upperarm_l'].translation).normalized()
                        .angle((pose['hand_l'].translation - pose['lowerarm_l'].translation).normalized()))
    right = math.degrees((pose['lowerarm_r'].translation - pose['upperarm_r'].translation).normalized()
                         .angle((pose['hand_r'].translation - pose['lowerarm_r'].translation).normalized()))
    shoulder_shift = max((pose['upperarm_l'].translation - idle_pose['upperarm_l'].translation).length,
                         (pose['upperarm_r'].translation - idle_pose['upperarm_r'].translation).length) * 100
    # Distance from the aiming line (the eye looks down +Y) to the blade segment.
    a, b = pose['Blade_Base'].translation, tip
    ab = b - a
    t = max(0.0, min(1.0, -ab.dot(a) / ab.length_squared))
    closest = a + ab * t
    rows.append({
        'seconds': seconds,
        'hilt': [round(v, 4) for v in hilt],
        'counterweight': [round(v, 4) for v in head],
        'blade_tip': [round(v, 4) for v in tip],
        'elbow_l': round(left, 1),
        'elbow_r': round(right, 1),
        'shoulder_shift_cm': round(shoulder_shift, 2),
        'blade_to_aim_line_m': round(math.hypot(closest.x, closest.z), 3),
        'blade_tip_in_front': bool(tip.y > 0.02),
    })
report['samples'] = rows

# Render: first person plus a three-quarter view of the striking arm.
for ob in scene.objects:
    ob.hide_render = ob not in (rig, arms, blade)
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 900
scene.render.resolution_y = 620
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('PommelWorld')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.30, .34, .40, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 1.1
for name, loc, energy, size in [('Key', (-.5, -.4, 1.1), 130, 1.3),
                                ('Fill', (.8, .4, .6), 80, 1.2),
                                ('Rim', (-.3, 1.2, .4), 100, .9)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.shape = 'DISK'
    light.size = size
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, .2, .1)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
data = bpy.data.cameras.new('PommelCamera')
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
scene.camera = camera
data.clip_start = .004

for seconds in FP_SHOTS:
    pose = set_time(pommel, seconds)
    camera.location = (0, 0, 0)
    camera.rotation_euler = Vector((0.02, 1.0, -0.06)).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'PERSP'
    data.lens = 17
    scene.render.filepath = str(REVIEW / ('fp_%03dms.png' % round(seconds * 1000)))
    bpy.ops.render.render(write_still=True)
    print('FP', seconds, flush=True)

for seconds in JOINT_SHOTS:
    pose = set_time(pommel, seconds)
    centre = (pose['upperarm_l'].translation + 2 * pose['lowerarm_l'].translation
              + pose['hand_l'].translation) / 4
    camera.location = centre + Vector((.35, -.75, .30)).normalized() * .7
    camera.rotation_euler = (Vector(centre) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'ORTHO'
    data.ortho_scale = .62
    scene.render.filepath = str(REVIEW / ('joint_%03dms.png' % round(seconds * 1000)))
    bpy.ops.render.render(write_still=True)
    print('JOINT', seconds, flush=True)

(P / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('%-8s %-26s %-26s %6s %6s %7s %8s' % ('time', 'hilt', 'counterweight', 'elbL', 'elbR', 'clav cm', 'blade X'))
for row in rows:
    print('%-8.2f %-26s %-26s %6.1f %6.1f %7.2f %8.3f' % (
        row['seconds'], row['hilt'], row['counterweight'], row['elbow_l'], row['elbow_r'],
        row['shoulder_shift_cm'], row['blade_to_aim_line_m']))
print('VERIFY_POMMEL_DONE')
