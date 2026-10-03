"""List armature/mesh/action names in the ASH-12 source blends."""
import bpy, json, sys
from pathlib import Path

JOB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
JOB.mkdir(parents=True, exist_ok=True)
S = JOB.parent
BLENDS = {
    'reload_empty': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                     'ASH12_EmptyReload_RightEdgeReachPullReturn'),
    'quick_melee': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                    'ASH12_QuickCombat_N_Base'),
    'idle': (S / 'ASH1220260917/ASH12_Editable.blend', 'ASH12_idle'),
}
out = {}
for key, (path, action) in BLENDS.items():
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    rigs = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    rig = rigs[0]
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    arm_meshes = [o for o in meshes if any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
    act = bpy.data.actions.get(action)
    out[key] = dict(blend=str(path), action=action, action_exists=act is not None,
                    rig=rig.name, rig_count=len(rigs),
                    armature_meshes=[o.name for o in arm_meshes],
                    groups=len(arm_meshes[0].vertex_groups) if arm_meshes else 0,
                    bones=len(rig.data.bones), frame_range=[bpy.context.scene.frame_start, bpy.context.scene.frame_end],
                    actions=sorted(a.name for a in bpy.data.actions)[:14],
                    has_hand_l='hand_l' in rig.data.bones, has_ik='ik_hand_l' in rig.data.bones)
    print('ASH12_BLEND', key, rig.name, 'arm_meshes', out[key]['armature_meshes'],
          'bones', len(rig.data.bones), 'action', action, act is not None)
    print('   actions', out[key]['actions'])
(JOB / 'blend_probe.json').write_text(json.dumps(out, indent=2))
