"""Read the existing authored poses needed to build tactical sprint."""
import bpy, json
from pathlib import Path
S = Path(__file__).resolve().parent.parent
sources = {
    'Base': 'M4ContactImpact20260910/M4_Hand_MAT_Editable.blend',
    'Angled': 'AngledForegrip20260910/WristNatural/A_M4_Foregrip_idle.blend',
    'Vertical': 'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend',
    'Canted': 'VREGripExtensions20260912/Final/m4/canted/A_M4_Canted_idle.blend',
    'Prism': 'VREGripExtensions20260912/Final/m4/prism/A_M4_Prism_idle.blend',
}
for profile, source in sources.items():
    bpy.ops.wm.open_mainfile(filepath=str(S / source))
    rig = bpy.data.objects['SK_M4_Infima']
    if profile == 'Base':
        action = bpy.data.actions['M4_idle']
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    print('SOURCE_POSE', json.dumps({'profile': profile,
        'action': rig.animation_data.action.name,
        'range': list(rig.animation_data.action.frame_range),
        'rig_scale': list(rig.scale),
        'positions': {n: list(rig.pose.bones[n].matrix.translation) for n in
            ['hand_r', 'hand_l', 'upperarm_r', 'lowerarm_r', 'upperarm_l', 'lowerarm_l', 'WPN_root', 'WPN_SOCKET_Muzzle']}}), flush=True)
