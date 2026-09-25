"""Read source FBX units needed to author pose-compatible derivatives."""
import bpy,json
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/inputs.json')
data=json.loads(p.read_text())
for key in ('Body','M4','PKM','SVD'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=data[key]['fbx'],use_anim=False)
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    print('AUTHOR_BINDING_UNITS',key,'armature',tuple(rig.scale),'hand_world_scale',tuple((rig.matrix_world@rig.data.bones['hand_r'].matrix_local).to_scale()),flush=True)
