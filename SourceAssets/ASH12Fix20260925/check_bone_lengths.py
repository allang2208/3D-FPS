"""Check bone-length constancy in the ASH-12 source actions and pose scales."""
import bpy, sys
from pathlib import Path

S = Path(r'D:\FPS3D\FPSGAME\SourceAssets')
CASES = {
    'reload_empty': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                     'ASH12_EmptyReload_RightEdgeReachPullReturn', [0, 60, 120, 126, 130, 140, 180, 198]),
    'quick_melee': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                    'ASH12_QuickCombat_N_Base', [0, 12, 24, 36, 54]),
}
for key, (blend, action, frames) in CASES.items():
    bpy.ops.wm.open_mainfile(filepath=str(blend), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    act = bpy.data.actions[action]
    print('====', key)
    for side in ('l', 'r'):
        un, fn, hn, cn = (f'upperarm_{side}', f'lowerarm_{side}', f'hand_{side}', f'clavicle_{side}')
        row = []
        for f in frames:
            rig.animation_data.action = act
            rig.animation_data.action_slot = act.slots[0]
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            P = {b.name: b.matrix.copy() for b in rig.pose.bones}
            l1 = (P[fn].translation - P[un].translation).length * 100
            l2 = (P[hn].translation - P[fn].translation).length * 100
            lc = (P[un].translation - P[cn].translation).length * 100
            sc = P[un].to_scale()
            row.append((f, round(l1, 3), round(l2, 3), round(lc, 3), tuple(round(v, 4) for v in sc)))
        print('  ', side, row)
