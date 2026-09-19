"""Inspect the edited bones' local rotation in both blends and the curve layout."""
import bpy, math, sys
from pathlib import Path

P = Path(__file__).parent
BLENDS = {'source': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
          'v43': P / 'AzureRunesword_ChargedErgoV43.blend'}
CLIPS = ('HeavyCharge', 'HeavyRelease', 'Slash1')
BONES = ('lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l')
FRAMES = {'HeavyCharge': (168, 960), 'HeavyRelease': (36, 480), 'Slash1': (408,)}
FPS = 480.0


def angle(q):
    return math.degrees(2 * math.atan2(math.sqrt(q.x ** 2 + q.y ** 2 + q.z ** 2), abs(q.w)))


for label, path in BLENDS.items():
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    print('=====', label, path.name)
    print('actions:', sorted(a.name for a in bpy.data.actions if 'RuneSword' in a.name))
    for clip in CLIPS:
        action = bpy.data.actions['A_RuneSword_' + clip]
        curves = [c for layer in action.layers for strip in layer.strips
                  for bag in strip.channelbags for c in bag.fcurves]
        edited = [c for c in curves if any(c.data_path.startswith('pose.bones["' + b + '"].')
                                          for b in BONES)]
        print('--', clip, 'slots', [s.name_display for s in action.slots],
              'curves', len(curves), 'edited curves', len(edited))
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        for f in FRAMES[clip]:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            parts = []
            for b in BONES:
                parts.append('%s %.2f' % (b.split('_')[1] + '_' + b.split('_')[-1], angle(rig.pose.bones[b].rotation_quaternion)))
            print('     f=%4d (%.3f s)  %s' % (f, f / FPS, '  '.join(parts)))
print('INSPECT_ACTIONS_DONE')
