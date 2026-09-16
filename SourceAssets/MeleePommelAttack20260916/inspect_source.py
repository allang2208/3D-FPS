"""Read the current two-handed sword authoring blend: bones, clips, grip frames.

Read-only companion for the fourth combo hit (counterweight strike). Prints the
rig layout, the action list, the idle/attack endpoints and the sword extents so
the new clip can be authored against the same rig without guessing.
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

SOURCE = Path(
    r"D:\FPS3D\FPSGAME\SourceAssets\RuneSword20260913\ChargedErgoV43"
    r"\AzureRunesword_ChargedHoldV45.blend")
OUT = Path(__file__).parent / 'source_inspection.json'

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']

report = {
    'source': str(SOURCE),
    'fps': scene.render.fps / scene.render.fps_base,
    'objects': sorted(o.name for o in bpy.data.objects),
    'actions': {},
    'bones': [b.name for b in rig.pose.bones],
    'rest': {},
    'idle_pose': {},
    'grip_in_root': {},
}

for action in bpy.data.actions:
    start, end = action.frame_range
    report['actions'][action.name] = [round(start, 3), round(end, 3),
                                      round((end - start) / (scene.render.fps / scene.render.fps_base), 4)]

watch = ['WPN_root', 'Blade_Base', 'Blade_Tip', 'Pommel', 'hand_l', 'hand_r',
         'lowerarm_l', 'lowerarm_r', 'upperarm_l', 'upperarm_r', 'clavicle_l', 'clavicle_r']
for name in watch:
    bone = rig.data.bones.get(name)
    if bone:
        report['rest'][name] = [round(v, 5) for v in bone.matrix_local.translation]


def snapshot(tag):
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    root = pose['WPN_root']
    entry = {'WPN_root': [round(v, 5) for v in root.translation]}
    for name in ('hand_l', 'hand_r', 'Blade_Base', 'Blade_Tip'):
        if name in pose:
            entry[name + '_world'] = [round(v, 5) for v in pose[name].translation]
            local = root.inverted() @ pose[name]
            entry[name + '_in_root'] = [round(v, 5) for v in local.translation]
    report.setdefault(tag, entry)
    if tag == 'idle_pose':
        for side in ('l', 'r'):
            hand = 'hand_' + side
            grip = root.inverted() @ pose[hand]
            report['grip_in_root'][hand] = {
                'translation': [round(v, 5) for v in grip.translation],
                'rotation_deg': [round(v, 3) for v in grip.to_euler('XYZ')],
            }


for clip in ('Idle', 'Slash1', 'Slash2', 'Thrust', 'HeavyCharge', 'HeavyRelease'):
    action = bpy.data.actions.get('A_RuneSword_' + clip)
    if not action:
        continue
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    frames = action.frame_range
    for tag, frame in (('first', frames[0]), ('last', frames[1])):
        scene.frame_set(int(round(frame)))
        bpy.context.view_layer.update()
        snapshot('%s_%s' % (clip, tag))

idle = next((bpy.data.actions.get(name) for name in
             ('A_RuneSword_Idle', 'Idle', 'REF_V44_Idle', 'REF_V43_Idle') if bpy.data.actions.get(name)), None)
if idle:
    rig.animation_data.action = idle
    rig.animation_data.action_slot = idle.slots[0]
    scene.frame_set(0)
    bpy.context.view_layer.update()
    snapshot('idle_pose')
    print('IDLE_ACTION', idle.name)

mesh = bpy.data.objects.get('SK_Manny_Arms_Export')
if mesh:
    report['arms_mesh'] = {'vertices': len(mesh.data.vertices)}

blade = bpy.data.objects.get('RuneSword_Blade')
if blade:
    corners = [blade.matrix_world @ Vector(corner) for corner in blade.bound_box]
    report['blade_bounds_local'] = {
        'min': [round(min(c[i] for c in corners), 4) for i in range(3)],
        'max': [round(max(c[i] for c in corners), 4) for i in range(3)],
    }

OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('INSPECT_DONE', OUT)
