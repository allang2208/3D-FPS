import unreal,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Replacement')
opts=unreal.FbxImportUI();opts.automated_import_should_detect_type=False
opts.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
opts.import_as_skeletal=False;opts.import_mesh=True;opts.import_animations=False;opts.import_materials=True;opts.import_textures=True
opts.static_mesh_import_data.set_editor_property('combine_meshes',True)
t=unreal.AssetImportTask();t.filename=str(out/'SM_M4_Assembled_Candidate.fbx');t.destination_path='/Game/Weapons/M4Replacement/Candidate';t.automated=True;t.replace_existing=False;t.save=True;t.options=opts
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
assert t.imported_object_paths, 'No imported M4 assets'
(out/'ue_candidate_import.json').write_text(json.dumps({'paths':list(t.imported_object_paths),'runtime_replaced':False},indent=2))
unreal.log('M4_CANDIDATE_IMPORT_OK')
