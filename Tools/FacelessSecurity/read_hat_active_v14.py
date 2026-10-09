import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V14/Diagnosis')
bp=u.load_asset('/Game/Monsters/FacelessSecurity/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
ss=u.get_engine_subsystem(u.SubobjectDataSubsystem);lib=u.SubobjectDataBlueprintFunctionLibrary
report={'pie_active':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),'body':cdo.get_editor_property('visual_mesh').get_path_name(),'hats':[]}
for handle in ss.k2_gather_subobject_data_for_blueprint(bp):
    obj=lib.get_object_for_blueprint(lib.get_data(handle),bp)
    if isinstance(obj,u.SecurityHatComponent):
        hat=obj.get_editor_property('static_mesh');report['hats'].append({'component':obj.get_path_name(),'mesh':hat.get_path_name() if hat else None,
             'head_bone':str(obj.get_editor_property('head_bone')),'attachment':str(obj.get_editor_property('head_attachment_transform'))})
(root/'active_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
