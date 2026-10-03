"""Bone hierarchy facts needed before moving the weapon root or re-solving arms."""
import bpy
from pathlib import Path

S = Path(r'D:\FPS3D\FPSGAME\SourceAssets')
BLENDS = {
    'reload_empty': S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
    'quick_melee': S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
}
for key, path in BLENDS.items():
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    print('====', key, 'bones', len(parent))
    for name in ('WPN_root', 'WPN_SOCKET_Muzzle', 'WPN_bolt', 'WPN_SOCKET_Magazine',
                 'hand_r', 'hand_l', 'ik_hand_r', 'ik_hand_l', 'root', 'pelvis', 'spine_03', 'clavicle_r'):
        print('   ', name, '-> parent', parent.get(name, 'ABSENT'))
    kids = [n for n, p in parent.items() if p == 'WPN_root']
    print('    WPN_root children', kids)
    print('    meshes', [o.name for o in bpy.context.scene.objects if o.type == 'MESH'][:8])
    for ob in bpy.context.scene.objects:
        if ob.type == 'MESH' and ob.name.startswith('ASH12'):
            print('    ', ob.name, 'groups', len(ob.vertex_groups),
                  'sample', sorted(g.name for g in ob.vertex_groups)[:8])
