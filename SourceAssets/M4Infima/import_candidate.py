import unreal,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima');dest='/Game/Weapons/M4InfimaV3'
def imp(file,options):
 t=unreal.AssetImportTask();t.filename=str(out/file);t.destination_path=dest;t.automated=True;t.replace_existing=True;t.save=True;t.options=options;unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH;o.import_as_skeletal=True;o.import_mesh=True;o.import_animations=False;o.import_materials=True;o.import_textures=True;o.create_physics_asset=False
o.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',True)
imp('SK_M4_Infima.fbx',o)
m=unreal.load_asset(dest+'/SK_M4_Infima');assert isinstance(m,unreal.SkeletalMesh)
sk=m.get_editor_property('skeleton');report={}
for c in json.loads((out/'export_report.json').read_text())['clips']:
 o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;o.import_as_skeletal=False;o.import_mesh=False;o.import_animations=True;o.skeleton=sk;o.import_materials=False;o.import_textures=False;o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
 name='A_AKM_'+c['clip'];imp(name+'.fbx',o);a=unreal.load_asset(dest+'/'+name);assert a;report[name]=a.get_play_length();assert abs(report[name]-c['duration'])<.04,(name,report[name],c)
(out/'ue_import_report.json').write_text(json.dumps(report,indent=2));unreal.log('M4_INFIMA_IMPORT_OK')



