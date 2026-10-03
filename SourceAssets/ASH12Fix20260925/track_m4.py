"""Track the M4 N reference quick melee in the M4 camera frame for comparison with ASH-12."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
S = HERE.parent
FRAMES = list(range(0, 55, 3))
BLEND = S / 'M4QuickMeleeRefine20260919N/Base/M4_QuickCombat_Base_Editable.blend'
ACTION = 'M4_QuickCombatRefineN_Base'
CAM = dict(eye=Vector((0.0, -0.10, 0.05)), right=Vector((1, 0, 0)),
           forward=Vector((0, 1, 0)), up=Vector((0, 0, 1)))
bpy.ops.wm.open_mainfile(filepath=str(BLEND), use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
act = bpy.data.actions[ACTION]
scene = bpy.context.scene


def cs(p):
    d = Vector(p) - CAM['eye']
    return [round(d.dot(CAM[k]) * 100, 1) for k in ('right', 'forward', 'up')]


rows = []
for f in FRAMES:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(f)
    bpy.context.view_layer.update()
    row = dict(frame=f)
    for b in ('WPN_root', 'WPN_SOCKET_Muzzle', 'hand_l', 'hand_r', 'lowerarm_l', 'lowerarm_r'):
        row[b] = cs(rig.matrix_world @ rig.pose.bones[b].matrix.translation)
    rows.append(row)
(HERE / 'track_m4_n.json').write_text(json.dumps(rows, indent=1))
for r in rows:
    print('M4N', r['frame'], 'wpn_root', r['WPN_root'], 'muzzle', r['WPN_SOCKET_Muzzle'],
          'hand_l', r['hand_l'], 'hand_r', r['hand_r'], flush=True)
