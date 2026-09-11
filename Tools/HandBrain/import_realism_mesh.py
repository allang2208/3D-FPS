import unreal,json
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/realism_v05');dest='/Game/Monsters/HandBrain/RealismV05';lib=unreal.EditorAssetLibrary
old=unreal.load_asset('/Game/Monsters/HandBrain/SK_HandBrain');assert old
def load(filename,name,opt):
 t=unreal.AssetImportTask();t.filename=str(r/filename);t.destination_path=dest;t.destination_name=name;t.options=opt;t.automated=True;t.replace_existing=True;t.save=True
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=unreal.load_asset(dest+'/'+name);assert a;return a
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH;o.import_as_skeletal=True;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False;o.create_physics_asset=False;o.skeleton=old.skeleton
mesh=load('SK_HandBrain_Realism.fbx','SK_HandBrain_Realism',o)
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;o.skeleton=old.skeleton;o.import_mesh=False;o.import_animations=True;o.import_materials=False;o.import_textures=False
o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
clip=load('A_HandBrain_Howl_Realism.fbx','A_HandBrain_Howl_Realism',o);assert abs(clip.get_play_length()-3)<.04
pa=unreal.HandBrainMonster.create_physics_asset(mesh);assert pa;lib.save_loaded_asset(pa,False);lib.save_loaded_asset(mesh,False)
clip.set_editor_property('enable_root_motion',False);lib.save_loaded_asset(clip,False)
(r/'mesh_import_report.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'physics':pa.get_path_name(),'howl_seconds':clip.get_play_length(),'blueprint_changed':False},indent=2))
unreal.log('HANDBRAIN_REALISM_MESH_IMPORTED')
