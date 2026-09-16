"""Is the sprint chop actually a different move from the first slash?"""
import bpy, json, sys
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twirl_model as model

SOURCES = (
    ('Slash1 (normal attack)', P.parent / 'ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend',
     'A_RuneSword_Slash1'),
    ('HeavyCharge (accepted raise)', P.parent / 'ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend',
     'A_RuneSword_HeavyCharge'),
    ('V49 Overhead chop', P / 'AzureRunesword_OverheadV49.blend', 'A_RuneSword_Overhead'),
)

for label, path, clip in SOURCES:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    mesh = bpy.data.objects['RuneSword_Blade']
    fps = scene.render.fps / scene.render.fps_base
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    geometry = model.sword_geometry(rest['WPN_root'], mesh)
    right_shoulder = rest['upperarm_r'].translation
    action = bpy.data.actions[clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    start, end = map(int, action.frame_range)
    rows = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        hand = rig.pose.bones['hand_r'].matrix.translation
        full = rig.pose.bones['WPN_root'].matrix @ rest['WPN_root'].inverted()
        tip = full @ geometry['high']
        rows.append({'seconds': frame / fps, 'hand_y': hand.y, 'hand_z': hand.z,
                     'tip_x': tip.x, 'tip_y': tip.y, 'tip_z': tip.z,
                     'reach': (hand - right_shoulder).length})
    span = rows[-1]['seconds'] - rows[0]['seconds']
    print('=== %s  (%.3f s, %d frames)' % (label, span, len(rows)))
    print('   hand z  %+.3f .. %+.3f  (travel %.3f m)'
          % (min(r['hand_z'] for r in rows), max(r['hand_z'] for r in rows),
             max(r['hand_z'] for r in rows) - min(r['hand_z'] for r in rows)))
    print('   hand y  %+.3f .. %+.3f' % (min(r['hand_y'] for r in rows),
                                         max(r['hand_y'] for r in rows)))
    print('   tip  z  %+.3f .. %+.3f  x %+.3f .. %+.3f  y %+.3f .. %+.3f'
          % (min(r['tip_z'] for r in rows), max(r['tip_z'] for r in rows),
             min(r['tip_x'] for r in rows), max(r['tip_x'] for r in rows),
             min(r['tip_y'] for r in rows), max(r['tip_y'] for r in rows)))
    print('   tip vertical travel %.3f m, horizontal travel %.3f m'
          % (max(r['tip_z'] for r in rows) - min(r['tip_z'] for r in rows),
             max(r['tip_x'] for r in rows) - min(r['tip_x'] for r in rows)))
    print('   frames with the tip in front of the camera: %d / %d'
          % (sum(1 for r in rows if r['tip_y'] > 0.0), len(rows)))
    print('   right hand reach %.3f .. %.3f m'
          % (min(r['reach'] for r in rows), max(r['reach'] for r in rows)))
print('PROBE_CHOP_VS_SLASH_DONE')
