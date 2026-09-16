"""Sample the accepted heavy charge/release on a coarse clock to pick segments."""
import bpy, sys
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twirl_model as model

SOURCE = P.parent / 'ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend'

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
mesh = bpy.data.objects['RuneSword_Blade']
fps = scene.render.fps / scene.render.fps_base
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
geometry = model.sword_geometry(rest['WPN_root'], mesh)


def dump(clip, step):
    action = bpy.data.actions[clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    end = action.frame_range[1]
    print('=== %s (%.3f s)' % (clip, end / fps))
    print('%7s %9s %9s %9s %9s %9s %9s' % ('sec', 'handY', 'handZ', 'pomY', 'pomZ',
                                            'tipY', 'tipZ'))
    seconds = 0.0
    while seconds <= end / fps + 1e-6:
        scene.frame_set(int(round(seconds * fps)))
        bpy.context.view_layer.update()
        hand = rig.pose.bones['hand_r'].matrix
        full = rig.pose.bones['WPN_root'].matrix @ rest['WPN_root'].inverted()
        tip = full @ geometry['high']
        pommel = full @ geometry['low']
        print('%7.3f %9.4f %9.4f %9.4f %9.4f %9.4f %9.4f'
              % (seconds, hand.translation.y, hand.translation.z,
                 pommel.y, pommel.z, tip.y, tip.z))
        seconds += step


dump('A_RuneSword_HeavyCharge', 0.1)
dump('A_RuneSword_HeavyRelease', 0.025)
print('PROBE_OVERHEAD_CURVE_DONE')
