import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
report={}
for role,path in {'original':'/Game/Monsters/WitchMeshy/OriginalRobeV05/SK_Witch_Meshy',
                  'rebuilt':'/Game/Monsters/WitchRebuilt/SK_WitchRebuilt',
                  'foundation':'/Game/Monsters/WitchFoundation/SK_WitchFoundation'}.items():
    mesh=u.load_asset(path);bounds=mesh.get_bounds();imp=mesh.get_editor_property('asset_import_data')
    report[role]={'origin':str(bounds.origin),'extent':str(bounds.box_extent),
                  'import_scale':imp.get_editor_property('import_uniform_scale'),
                  'convert_units':imp.get_editor_property('convert_scene_unit')}
cls=u.load_class(None,'/Script/FPSGAME.WitchRebuiltMonster');cdo=u.get_default_object(cls)
report['class']={'actor_scale':str(cdo.get_actor_scale3d()),'mesh_scale':str(cdo.get_editor_property('mesh').get_editor_property('relative_scale3d'))}
(root/'ue_scale_repair_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
