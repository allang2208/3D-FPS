"""List armature/mesh/action names in the ten SVD reload source blends."""
import bpy, sys, json
from pathlib import Path

JOB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925')
S = JOB.parent
BLENDS = []
for family in ['base', 'vertical', 'canted', 'prism', 'angled']:
    if family == 'base':
        BLENDS.append(('reload', family, S / 'SVDThumbUp20260923/SVD_base_Editable.blend'))
        BLENDS.append(('reload_empty', family, S / 'SVDChargeGrasp20260924/SVD_base_Grasp.blend'))
    else:
        BLENDS.append(('reload', family, S / f'SVDThumbUp20260923/SVD_{family}_Editable.blend'))
        BLENDS.append(('reload_empty', family, S / f'SVDChargeGrasp20260924/SVD_{family}_Grasp.blend'))

out = {}
for clip, family, path in BLENDS:
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    rigs = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    rig = rigs[0]
    current = rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None
    out[f'{family}/{clip}'] = dict(blend=str(path), rig=rig.name, mesh=[o.name for o in bpy.context.scene.objects if o.type == 'MESH'][:6],
                                   current_action=current, actions=sorted(a.name for a in bpy.data.actions),
                                   frame_range=[bpy.context.scene.frame_start, bpy.context.scene.frame_end])
    print('BLEND', family, clip, rig.name, current, sorted(a.name for a in bpy.data.actions)[:8], flush=True)
(JOB / 'blend_probe.json').write_text(json.dumps(out, indent=1))
