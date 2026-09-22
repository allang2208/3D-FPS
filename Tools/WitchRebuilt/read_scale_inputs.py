"""Read reference dimensions needed to repair the reported enlargement. No render."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
sources={'original':ROOT.parent/'WitchMeshy20260919/Authoring/CleanRobeV06/Witch_CleanRobeV06.blend',
         'rebuilt':ROOT/'Authoring/WitchRebuilt_Master.blend',
         'rebuilt_idle':ROOT/'Authoring/WitchRebuilt_Idle.blend',
         'foundation':ROOT.parent/'WitchFoundation20260920/Authoring/WitchFoundation_Idle.blend',
         'delivery':ROOT/'Delivery/SK_WitchRebuilt.fbx'}
report={}
for key,path in sources.items():
    if path.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(path))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    data={'units':bpy.context.scene.unit_settings.scale_length,'rig_matrix':[list(row) for row in rig.matrix_world],'meshes':{},'bones':{}}
    for name in ('pelvis','head','foot_l','Hips','Head','LeftFoot'):
        if name in rig.data.bones:data['bones'][name]=list((rig.matrix_world@rig.data.bones[name].matrix_local).translation)
    for o in bpy.context.scene.objects:
        if o.type!='MESH' or 'Proxy' in o.name:continue
        pts=[o.matrix_world@v.co for v in o.data.vertices]
        data['meshes'][o.name]={'scale':list(o.scale),'min':[min(p[k] for p in pts) for k in range(3)],'max':[max(p[k] for p in pts) for k in range(3)]}
    report[key]=data
(ROOT/'scale_repair_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
