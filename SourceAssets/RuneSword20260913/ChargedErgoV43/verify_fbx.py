"""Read the exported FBX back and check structure, timing and the new rolls."""
import bpy, json, math, sys
from pathlib import Path

P = Path(__file__).parent
CLIPS = ('HeavyCharge', 'HeavyRelease', 'Slash1')
EXPECTED_SECONDS = {'HeavyCharge': 2.0, 'HeavyRelease': 1.0, 'Slash1': 1.775}
BONES = ('lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l')
SCENE_FPS = 480

report = {}
for clip in CLIPS:
    bpy.ops.wm.read_homefile(use_empty=True)
    path = P / 'Export' / ('A_RuneSword_' + clip + '.fbx')
    bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)
    rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    rig = rigs[0]
    actions = [a for a in bpy.data.actions]
    action = actions[0]
    rig.animation_data_create()
    rig.animation_data.action = action
    if hasattr(action, 'slots') and action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene = bpy.context.scene
    scene.render.fps = SCENE_FPS
    start, end = action.frame_range
    samples = {}
    for frame in (int(start), int(start + (end - start) * .175), int(end)):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        samples[frame] = {b: round(math.degrees(2 * math.atan2(
            math.sqrt(rig.pose.bones[b].rotation_quaternion.x ** 2
                      + rig.pose.bones[b].rotation_quaternion.y ** 2
                      + rig.pose.bones[b].rotation_quaternion.z ** 2),
            abs(rig.pose.bones[b].rotation_quaternion.w))), 2)
            for b in BONES if b in rig.pose.bones}
    report[clip] = {
        'file': str(path),
        'size': path.stat().st_size,
        'armatures': len(rigs),
        'bones': len(rig.data.bones),
        'has_twist_helpers': all(b in rig.data.bones for b in BONES[1:3]),
        'action': action.name,
        'frame_range': [start, end],
        'seconds': (end - start) / SCENE_FPS,
        'expected_seconds': EXPECTED_SECONDS[clip],
        'local_rotation_deg': samples,
    }

(P / 'fbx_readback.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for clip, entry in report.items():
    print('===', clip, 'bones', entry['bones'], 'helpers', entry['has_twist_helpers'],
          'frames', entry['frame_range'], 'seconds %.3f (expect %.3f)'
          % (entry['seconds'], entry['expected_seconds']))
    for frame, values in entry['local_rotation_deg'].items():
        print('   f=%s' % frame, values)
print('VERIFY_FBX_DONE')
