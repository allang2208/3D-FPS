"""Camera-space track of the weapon and both arms for the ASH-12 clips (baseline: idle)."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
S = HERE.parent
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CLIP = ARGS[0]
FRAMES = [int(v) for v in ARGS[1:] if v.lstrip('-').isdigit()]
CLIPS = {
    'reload_empty': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                     'ASH12_EmptyReload_RightEdgeReachPullReturn'),
    'quick_melee': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                    'ASH12_QuickCombat_N_Base'),
    'idle': (S / 'ASH1220260917/ASH12_Editable.blend', 'ASH12_idle'),
}
CAM = dict(eye=Vector((-0.07281457632780075, -0.19707617163658142, 0.12465998530387878)),
           right=Vector((0.9999997615814209, -0.0007808567606844008, 0.0)),
           forward=Vector((0.000780856644269079, 0.9999996423721313, -9.368201426696032e-05)),
           up=Vector((7.315222205761529e-08, 9.368197788717225e-05, 1.0)))

blend, action_name = CLIPS[CLIP]
bpy.ops.wm.open_mainfile(filepath=str(blend), use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
act = bpy.data.actions[action_name]
scene = bpy.context.scene


def cs(p):
    d = Vector(p) - CAM['eye']
    return [round(d.dot(CAM[k]) * 100, 1) for k in ('right', 'forward', 'up')]


BONES = ['WPN_root', 'WPN_SOCKET_Muzzle', 'hand_l', 'hand_r', 'lowerarm_l', 'lowerarm_r',
         'upperarm_l', 'upperarm_r', 'pelvis', 'spine_03']
rows = []
for f in FRAMES:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(f)
    bpy.context.view_layer.update()
    row = dict(frame=f)
    for b in BONES:
        row[b] = cs(rig.matrix_world @ rig.pose.bones[b].matrix.translation)
    rows.append(row)
(HERE / f'track_{CLIP}.json').write_text(json.dumps(rows, indent=1))
for r in rows:
    print('TRACK', CLIP, r['frame'],
          'wpn_root', r['WPN_root'], 'muzzle', r['WPN_SOCKET_Muzzle'],
          'hand_l', r['hand_l'], 'elbow_l', r['lowerarm_l'],
          'hand_r', r['hand_r'], 'elbow_r', r['lowerarm_r'], flush=True)
