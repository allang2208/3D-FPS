"""Compare exported FBX world poses against the authoring blend."""
import bpy, json, math
from pathlib import Path

P = Path(__file__).parent
BLEND = P / 'AzureRunesword_ChargedErgoV43.blend'
CLIPS = {'HeavyCharge': (0.0, 0.35, 2.0), 'HeavyRelease': (0.0, 0.6, 1.0),
         'Slash1': (0.0, 0.85, 1.775)}
FPS = 480.0
BONES = ('upperarm_l', 'lowerarm_l', 'hand_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l')


def read_blend():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    out = {}
    for clip, times in CLIPS.items():
        action = bpy.data.actions['A_RuneSword_' + clip]
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        for t in times:
            scene.frame_set(int(round(t * FPS)))
            bpy.context.view_layer.update()
            out['%s %.3f' % (clip, t)] = {b: [round(v, 6) for v in rig.pose.bones[b].matrix.translation]
                                          for b in BONES}
    return out


def read_fbx():
    out = {}
    for clip, times in CLIPS.items():
        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(P / 'Export' / ('A_RuneSword_' + clip + '.fbx')),
                                 automatic_bone_orientation=False)
        rig = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
        action = bpy.data.actions[0]
        rig.animation_data_create()
        rig.animation_data.action = action
        if hasattr(action, 'slots') and action.slots:
            rig.animation_data.action_slot = action.slots[0]
        scene = bpy.context.scene
        scene.render.fps = int(FPS)
        start = action.frame_range[0]
        for t in times:
            scene.frame_set(int(round(start + t * FPS)))
            bpy.context.view_layer.update()
            out['%s %.3f' % (clip, t)] = {b: [round(v, 6) for v in rig.pose.bones[b].matrix.translation]
                                          for b in BONES}
    return out


blend = read_blend()
fbx = read_fbx()
summary = {}
for key, values in blend.items():
    others = fbx.get(key)
    if not others:
        continue
    worst = 0.0
    worst_bone = ''
    for bone, position in values.items():
        delta = math.dist(position, others[bone]) * 100.0
        if delta > worst:
            worst, worst_bone = delta, bone
    summary[key] = {'max_position_delta_cm': worst, 'bone': worst_bone,
                    'blend': values, 'fbx': others}
(P / 'fbx_world_check.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
for key, entry in summary.items():
    print('%-22s max world position delta %8.4f cm (%s)' % (key, entry['max_position_delta_cm'], entry['bone']))
print('VERIFY_FBX_WORLD_DONE')
