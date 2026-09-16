"""Find the point of the shipped twirl that stays put in the hand.

The pivot is not something to guess from the bone origins: it is the point of
the sword that stays closest to fixed in the hand's frame over the spin, which
is what the fitted animation actually turns the sword about.  Sampling the
sword's own axis answers it directly, and the answer also says how much of the
hilt slides through the hand.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCES = {
    'v42': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
}
import sys
sys.path.insert(0, str(P))
import twirl_model as model

FPS = 120.0
CLIP = 'A_RuneSword_Inspect'
SPIN = (0.350, 0.650)
SAMPLES = 121

report = {}
for label, path in SOURCES.items():
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    mesh = bpy.data.objects['RuneSword_Blade']
    action = bpy.data.actions[CLIP]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    geometry = model.sword_geometry(rest['WPN_root'], mesh)
    pommel, tip = geometry['low'], geometry['high']

    samples = []
    for frame in range(int(SPIN[0] * FPS), int(SPIN[1] * FPS) + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        hand = rig.pose.bones['hand_r'].matrix
        sword = rig.pose.bones['WPN_root'].matrix @ rest['WPN_root'].inverted()
        samples.append({'hand_inverse': hand.inverted(), 'sword': sword})

    curve = []
    for index in range(SAMPLES):
        t = index / (SAMPLES - 1)
        point_local = pommel.lerp(tip, t)
        positions = [sample['hand_inverse'] @ (sample['sword'] @ point_local)
                     for sample in samples]
        mean = sum(positions, Vector()) / len(positions)
        rms = math.sqrt(sum((position - mean).length_squared
                            for position in positions) / len(positions))
        curve.append({'t': round(t, 4), 'rms_m': round(rms, 5),
                      'mean_hand_local': [round(v, 4) for v in mean]})
    best = min(curve, key=lambda entry: entry['rms_m'])
    report[label] = {'sword_length_m': round(geometry['length'], 4),
                     'pommel_local': [round(v, 4) for v in pommel],
                     'tip_local': [round(v, 4) for v in tip],
                     'best': best,
                     'curve': curve}
    print('=== %s  sword %.4f m' % (label, geometry['length']))
    print('pommel (near hand?) %s -> tip %s'
          % ([round(v, 4) for v in pommel], [round(v, 4) for v in tip]))
    print('best fixed point t=%.3f  rms %.4f m  mean in hand frame %s'
          % (best['t'], best['rms_m'], best['mean_hand_local']))
    for entry in curve[::10]:
        print('   t=%.3f rms=%.4f m  mean=%s'
              % (entry['t'], entry['rms_m'], entry['mean_hand_local']))

(P / 'probe_contact_point.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PROBE_CONTACT_POINT_DONE')
